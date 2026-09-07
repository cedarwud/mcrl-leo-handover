#!/usr/bin/env python3
"""Isolated, pre-outcome C3 persistent-power Stage-0 runner.

This module intentionally contains no learner, replay, reward, or retired-rule
code.  The runner is an adapter boundary: a frozen environment implementation
supplies replay/roll-forward observations, while this file owns the sealed
selection, twin, branch, and aggregation contracts.  The command line entry
point is fail-closed until an explicit seed manifest and closure manifest have
been created after the gate is reviewed.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
import pickle
import platform
import statistics
import sys
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DESIGN_DIR = REPO / ".scratch" / "catfish-design-data"
ORACLE_DIR = REPO / ".scratch" / "catfish-oracle-gate"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(DESIGN_DIR))
sys.path.insert(0, str(ORACLE_DIR))

import run_oracle_gate as oracle  # noqa: E402
import scripts.run_head_pivotality_probe as checkpoint_loader  # noqa: E402
from mcrl.env.action_contract import (  # noqa: E402
    NO_OP_ACTION,
    Association,
    HandoverClass,
    UNSERVED,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.link_budget import pa_efficiency, supply_power_w  # noqa: E402
from mcrl.runtime.head_pivotality import (  # noqa: E402
    masked_greedy_actions,
    physical_action_keys,
)
from mcrl.runtime.prereg import read_prereg  # noqa: E402
from mcrl.runtime.training_pipeline import (  # noqa: E402
    _code_sha256,
    _default_code_paths,
    _evaluation_rngs,
)


SPEC_PATH = DESIGN_DIR / "C3-PERSISTENT-POWER-STAGE0-SPEC-2026-08-27.md"
METHOD_PATH = REPO / "docs" / "MULTI-CATFISH-PAPER-ALGORITHM-V0.4-2026-08-27.md"
OTHER_SPEC_PATH = DESIGN_DIR / "C2-PERSISTENCE-OPTION-STAGE0-SPEC-2026-08-27.md"
SOURCE_DRIFT_MANIFEST = DESIGN_DIR / "C3-ANALYSIS-SOURCE-DRIFT-MANIFEST-2026-08-27.md"
HELPER_CLOSURE_MANIFEST = DESIGN_DIR / "C3-HELPER-CLOSURE-MANIFEST-2026-08-27.md"
C3_V1_HELPER = DESIGN_DIR / "run_c3_intra_bottleneck_shadow.py"
C3_DISJOINT_HELPER = DESIGN_DIR / "run_c3_disjoint_median_shadow.py"
ORACLE_HELPER = ORACLE_DIR / "run_oracle_gate.py"
CHECKPOINT_LOADER_HELPER = REPO / "scripts" / "run_head_pivotality_probe.py"
DEFAULT_INPUT = REPO / "artifacts" / "training-2026-08-25-rerun01"
DEFAULT_PREREG = REPO / "artifacts" / "PREREG-FROZEN-2026-08-25-R2.json"
EXPECTED_SPEC_SHA256 = (
    "20bf5cd45d05bc8438fab2bfcfd85ba02783fbd0623112cac6aff8db9316b70d"
)
EXPECTED_METHOD_SHA256 = (
    "d2444e83a8b98cd2d782d622a4768d77e6651928b0fe1af544138b9548182416"
)
EXPECTED_COMPANION_SPEC_SHA256 = (
    "b14114112b9548428165089c709735d411f00c2c3cf74af075ced5ae6dd3d716"
)
EXPECTED_CHECKPOINT_SHA256 = (
    "e6b063efea8608fd1e46ac15d5442aa8d1171dffc9f0b5e8cc209eca1b09c28b"
)
EXPECTED_PREREG_SHA256 = (
    "8bf13e289e18d663699a39c778dfe5af5b7538781c08b42bf5d085776cd44543"
)
EXPECTED_ANALYSIS_CODE_SHA256 = (
    "4cfc7e3043453994fc0686c3bbfa14d9a95156aeabc578b26decb2f210603a2e"
)
EXPECTED_SOURCE_DRIFT_MANIFEST_SHA256 = (
    "d3f4c2f78dfaa8bb9a94d5a988c6420b3875f50dfcf6a5e9bb54735187edf76c"
)
EXPECTED_HELPER_CLOSURE_MANIFEST_SHA256 = (
    "575e7745216bb171808224be000b5538ce047e88e703902731d13335ccf104f0"
)
EXPECTED_C3_V1_HELPER_SHA256 = (
    "c9558d4db702bc3a84efc00b92e809f9a190409a9b6f286cb225e5ce52a40706"
)
EXPECTED_ORACLE_HELPER_SHA256 = (
    "b50c396ea344d444e5db704aea05db613f9d6e29930524185d0f33f3cee338cb"
)
EXPECTED_CHECKPOINT_LOADER_SHA256 = (
    "563c5c5fa04068868d02cbce542dc3a15305fd840b766dc919f257ea49dddeb9"
)
POWER_TOLERANCE_W = 1e-10
STRICT_MAX_TOLERANCE_W = 1e-12
DELTA_S = 30.08
H3 = 3
T95 = 2.776445105
SEED_COUNT = 5
USERS = 100
STEPS = 10
ANCHOR_STEPS = frozenset(range(8))
SEED_SCHEMA = "smc-er-c3-stage0-seeds-v1"
CLOSURE_SCHEMA = "smc-er-c3-stage0-closure-v1"
OUTPUT_SCHEMA = "smc-er-c3-stage0-result-v1"
PASS_RESULT = "C3_STAGE0_PASS_TO_IMPLEMENTATION_RULING_ONLY"
CERTIFICATE_FAILURE = "C3_STAGE0_CERTIFICATE_FAILURE"
DROP_ROLE = "C3_STAGE0_FAIL_DROP_ROLE"
NAMESPACES = {
    "forecast": "SMC-ER-C3-H3-v1",
    "cert_control": "SMC-ER-C3-CERT-R-v1",
    "rank_control": "SMC-ER-C3-RANK-R-v1",
}

PhysicalKey = tuple[int, int]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dt.datetime):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def sha256_file(path: Path) -> str:
    """Return the byte hash of *path* without normalising text."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    """Canonical JSON used by every sealed derivation and receipt hash."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=_json_default,
    ).encode("utf-8")


def state_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def opaque_seed_id(seed: Any) -> str:
    """Identify a seed in receipts without publishing the seed value itself."""

    return state_sha256(["SMC-ER-C3-seed-receipt-v1", seed])


def derive_rng(
    namespace: str,
    checkpoint_sha256: str,
    evaluation_seed: int,
    step_index: int,
    focal_user: int,
) -> np.random.Generator:
    """Derive the exact domain-separated PCG64 stream from the frozen spec."""

    if namespace not in NAMESPACES.values():
        raise ValueError(f"unknown frozen RNG namespace: {namespace}")
    payload = canonical_json(
        [namespace, checkpoint_sha256, int(evaluation_seed), int(step_index), int(focal_user)]
    )
    integer = int.from_bytes(hashlib.sha256(payload).digest()[:16], "big")
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(integer)))


def rng_state_sha256(rng: np.random.Generator) -> str:
    return state_sha256(rng.bit_generator.state)


def choose_uniform(rng: np.random.Generator, physical_ids: Sequence[Any]) -> Any:
    """Choose one item without sorting or filtering based on an outcome."""

    if not physical_ids:
        raise ValueError("cannot choose from an empty support")
    return physical_ids[int(rng.integers(0, len(physical_ids)))]


def remap_action_by_physical_id(
    candidate_table: Mapping[Any, int] | Sequence[tuple[Any, int]],
    physical_id: Any,
) -> int:
    """Resolve a committed physical ID after a candidate-table rebuild."""

    mapping = dict(candidate_table)
    try:
        return int(mapping[physical_id])
    except KeyError as exc:
        raise RuntimeError("committed physical association disappeared") from exc


def _rng_sha(rng: np.random.Generator | None) -> str | None:
    return None if rng is None else rng_state_sha256(rng)


def _object_sha(value: Any) -> str:
    return hashlib.sha256(pickle.dumps(value, protocol=5)).hexdigest()


def _array_sha(value: Any) -> str | None:
    return None if value is None else _object_sha(np.asarray(value))


def _association_receipt(value: Any) -> dict[str, Any]:
    if isinstance(value, Association):
        return {
            "kind": "association",
            "norad_id": int(value.norad_id),
            "cell_id": int(value.cell_id),
        }
    if value is None:
        return {"kind": "episode_start"}
    # The private UNSERVED sentinel is intentionally classified by type so a
    # copied sentinel cannot change the anchor fingerprint.
    if isinstance(value, type(UNSERVED)):
        return {"kind": "unserved"}
    raise TypeError(f"unexpected association state: {value!r}")


def _wrapped_mutable_state_receipt(wrapped: Any) -> dict[str, Any]:
    """Capture every mutable anchor field used by the frozen environment."""

    environment = wrapped.environment
    driver = environment.driver
    tracker = driver._tracker
    satellites = driver._satellites
    return {
        "wrapper": {
            "epoch": None if wrapped._epoch is None else wrapped._epoch.isoformat(),
            "last_outcome_sha256": (
                None
                if wrapped._last_outcome is None
                else _object_sha(wrapped._last_outcome)
            ),
        },
        "environment": {
            "step_index": int(environment._step_index),
            "started": bool(environment._started),
            "ledgers": [
                {
                    "previous": _association_receipt(ledger.previous),
                    "started": bool(ledger._started),
                }
                for ledger in environment._ledgers
            ],
            "segments_sha256": _object_sha(environment._segments),
            "previous_radiating_sha256": _object_sha(environment._previous_radiating),
            "previous_demand": [
                [int(key[0]), int(key[1]), int(value)]
                for key, value in sorted(environment._previous_demand.items())
            ],
            "previous_association": [
                _association_receipt(value)
                for value in environment._previous_association
            ],
            "candidates_sha256": (
                None
                if environment._candidates is None
                else _object_sha(environment._candidates)
            ),
            "pending_segment_age_sha256": _array_sha(environment._pending_segment_age),
            "mobility_rng_sha256": _rng_sha(environment._mobility_rng),
            "age_rng_sha256": _rng_sha(environment._age_rng),
        },
        "scenario_driver": {
            "step_index": int(driver._step_index),
            "start_utc": None if driver._start_utc is None else driver._start_utc.isoformat(),
            "frozen_window_norad_ids_sha256": _array_sha(driver._frozen_window_norad_ids),
            "user_xy_km_sha256": _array_sha(driver._users._xy_km),
            "user_heading_rad_sha256": _array_sha(driver._users._heading_rad),
            "dwell_anchors_sha256": _array_sha(driver._dwell._anchors),
            "satellite_norad_ids_sha256": (
                None if satellites is None else _array_sha(satellites.norad_ids)
            ),
            "satellite_tle_records_sha256": (
                None if satellites is None else _object_sha(satellites.records)
            ),
            "d2_tracker": (
                None
                if tracker is None
                else {
                    "latched_sha256": _array_sha(tracker._latched),
                    "condition_active_sha256": _array_sha(tracker._condition_active),
                    "condition_started_sha256": _array_sha(tracker._condition_started),
                    "ttt_elapsed_sha256": _array_sha(tracker._ttt_elapsed),
                    "steps_seen": int(tracker._steps_seen),
                    "primed": bool(tracker._primed),
                }
            ),
        },
    }


def pa_identity_residual(
    realised_delta_system_power_w: float,
    *,
    reference_max_power_w: float,
    reference_next_power_w: float,
    supply_power: Callable[[float], float],
) -> float:
    """Residual of the exact PA recurrence used by the H3 certificate."""

    predicted = supply_power(reference_next_power_w) - supply_power(reference_max_power_w)
    return float(realised_delta_system_power_w - predicted)


class TwinFactory(Protocol):
    """Adapter required by the certificate and post-selection evaluator."""

    def replay_prefix(self, anchor: Mapping[str, Any]) -> Any: ...

    def fingerprint(self, twin: Any) -> str: ...


class RollForward(Protocol):
    def __call__(self, twin: Any, focal_physical_id: Any, interval: int,
                 forecast_rng: np.random.Generator) -> Mapping[str, Any]: ...


def replay_twins(
    factory: TwinFactory, anchor: Mapping[str, Any]
) -> tuple[Any, Any, str]:
    """Rebuild two twins by replaying the frozen prefix, then certify equality.

    The factory is deliberately the only state-construction seam.  In
    particular, this function never calls ``copy`` or accesses an environment
    snapshot/private clone API.
    """

    reference = factory.replay_prefix(anchor)
    candidate = factory.replay_prefix(anchor)
    reference_fingerprint = factory.fingerprint(reference)
    candidate_fingerprint = factory.fingerprint(candidate)
    if reference_fingerprint != candidate_fingerprint:
        raise RuntimeError("replayed twin anchor fingerprints differ")
    return reference, candidate, reference_fingerprint


@dataclass(frozen=True)
class CertificateResult:
    candidate_id: Any
    certified: bool
    reasons: tuple[str, ...]
    gain_j: float | None
    intervals: tuple[Mapping[str, Any], ...]
    forecast_objects_distinct: bool = True
    forecast_initial_state_sha256: str | None = None
    forecast_final_state_sha256: tuple[str, str] | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        return bool(np.array_equal(a, b))
    return a == b


def certify_candidate(
    *,
    source_id: Any,
    candidate_id: Any,
    reference_twin: Any,
    candidate_twin: Any,
    twin_factory: TwinFactory,
    roll_forward: RollForward,
    forecast_rng_reference: np.random.Generator,
    forecast_rng_candidate: np.random.Generator,
    supply_power: Callable[[float], float] | None = None,
) -> CertificateResult:
    """Apply the frozen H3 certificate to one physical-ID candidate.

    ``roll_forward`` must return pre-outcome deterministic records with the
    fields used below.  It is deliberately not given an eventual environment
    RNG.  Reference and candidate actions are generated independently by the
    adapter, then compared by physical ID.
    """

    reasons: list[str] = []
    supply = supply_power or (lambda value: float(value))
    initial_forecast_state = rng_state_sha256(forecast_rng_reference)
    if forecast_rng_reference is forecast_rng_candidate:
        reasons.append("forecast_rng_objects_not_distinct")
    if twin_factory.fingerprint(reference_twin) != twin_factory.fingerprint(candidate_twin):
        reasons.append("anchor_fingerprint_mismatch")
    if rng_state_sha256(forecast_rng_reference) != rng_state_sha256(forecast_rng_candidate):
        reasons.append("forecast_rng_initial_state_mismatch")
    records: list[Mapping[str, Any]] = []
    gain = 0.0
    for interval in range(H3):
        ref = roll_forward(reference_twin, source_id, interval, forecast_rng_reference)
        cand = roll_forward(candidate_twin, candidate_id, interval, forecast_rng_candidate)
        records.append({"reference": ref, "candidate": cand, "interval": interval})
        for field, label in (
            ("nonfocal_actions", "nonfocal_action_mismatch"),
            ("served_users", "served_set_mismatch"),
            ("active_beams", "active_beam_set_mismatch"),
            ("active_satellites", "active_satellite_set_mismatch"),
        ):
            if not _same(ref.get(field), cand.get(field)):
                reasons.append(label)
        if not bool(cand.get("reference_hold_valid", True)):
            reasons.append("candidate_hold_invalid")
        if not bool(ref.get("reference_hold_valid", True)):
            reasons.append("reference_hold_invalid")
        if not bool(cand.get("service", False)):
            reasons.append("candidate_service_failure")
        if not bool(cand.get("destination_max_unchanged", False)):
            reasons.append("destination_max_changed")
        if not bool(cand.get("source_bottleneck_relief", False)):
            reasons.append("source_bottleneck_relief_not_persistent")
        candidate_power = cand.get("system_payload_power_w", cand.get("system_power_w"))
        reference_power = ref.get("system_payload_power_w", ref.get("system_power_w"))
        if candidate_power is None or reference_power is None:
            reasons.append("system_power_evidence_missing")
        elif float(candidate_power) >= float(reference_power):
            reasons.append("candidate_power_not_strictly_lower")
        reference_max = cand.get("reference_max_power_w", cand.get("source_max_power_w"))
        reference_next = cand.get("reference_next_power_w", cand.get("source_next_power_w"))
        reference_system = ref.get("system_payload_power_w", ref.get("system_power_w"))
        candidate_system = cand.get("system_payload_power_w", cand.get("system_power_w"))
        if any(value is None for value in (reference_max, reference_next, reference_system, candidate_system)):
            reasons.append("pa_recurrence_evidence_missing")
        else:
            predicted = supply(float(reference_next)) - supply(float(reference_max))
            realised = float(candidate_system) - float(reference_system)
            residual = realised - predicted
            if abs(residual) > POWER_TOLERANCE_W:
                reasons.append("candidate_pa_identity_failure")
        if not bool(cand.get("preview_commit_parity", True)):
            reasons.append("preview_commit_parity_failure")
        gain += DELTA_S * (
            (float(reference_power) if reference_power is not None else math.nan)
            - (float(candidate_power) if candidate_power is not None else math.nan)
        )
        if interval == 0:
            if int(cand.get("phi1", 0)) - int(ref.get("phi1", 0)) != 1:
                reasons.append("initial_phi1_count_not_exactly_one_additional")
            if int(cand.get("phi2", 0)) != int(ref.get("phi2", 0)):
                reasons.append("initial_phi2_changed")
        else:
            if int(cand.get("phi1", 0)) != int(ref.get("phi1", 0)):
                reasons.append("later_phi1_event")
            if int(cand.get("phi2", 0)) != int(ref.get("phi2", 0)):
                reasons.append("later_phi2_event")
    unique_reasons = tuple(dict.fromkeys(reasons))
    # Certification is conditions 1--8 only.  A positive gain is a terminal
    # selected-pass safeguard, not a reason to erase a condition-valid row.
    certified = not unique_reasons and math.isfinite(gain)
    return CertificateResult(
        candidate_id=candidate_id,
        certified=certified,
        reasons=unique_reasons,
        gain_j=float(gain) if math.isfinite(gain) else None,
        intervals=tuple(records),
        forecast_objects_distinct=forecast_rng_reference is not forecast_rng_candidate,
        forecast_initial_state_sha256=initial_forecast_state,
        forecast_final_state_sha256=(
            rng_state_sha256(forecast_rng_reference),
            rng_state_sha256(forecast_rng_candidate),
        ),
        evidence={
            "pa_recurrence_checked_independently": True,
            "conditions_1_to_8_only": True,
        },
    )


def select_top_gain(results: Iterable[CertificateResult]) -> CertificateResult | None:
    """Select by G_P, then lexicographic physical ID."""

    survivors = [result for result in results if result.certified]
    if not survivors:
        return None
    return sorted(
        survivors, key=lambda result: (-float(result.gain_j), result.candidate_id)
    )[0]


def select_rank_control(
    results: Iterable[CertificateResult], rng: np.random.Generator
) -> Any:
    certified = [result.candidate_id for result in results if result.certified]
    return choose_uniform(rng, certified)


def select_certificate_control(
    hard_safe_physical_ids: Sequence[Any], rng: np.random.Generator
) -> Any:
    """Draw C3-CERT-R from broader hard-safe support before certification."""

    return choose_uniform(rng, hard_safe_physical_ids)


@dataclass(frozen=True)
class BranchOutcome:
    name: str
    useful_bits: float
    payload_energy_j: float
    canonical_ee: float
    service: bool
    intervals: tuple[Mapping[str, Any], ...]
    evidence: Mapping[str, Any] = field(default_factory=dict)


def validate_branch_contract(outcomes: Mapping[str, BranchOutcome]) -> None:
    """Check the common-realised-path safeguards across four branches."""

    required = {"reference", "top_gp", "C3-RANK-R", "C3-CERT-R"}
    if set(outcomes) != required:
        raise ValueError(f"four branches required; got {sorted(outcomes)}")
    for branch in outcomes.values():
        if not branch.service:
            raise RuntimeError(f"service failure in {branch.name}")
        if len(branch.intervals) != H3:
            raise RuntimeError(f"{branch.name} must contain exactly H3 intervals")
        if any(row.get("fading_enabled") is not False for row in branch.intervals):
            raise RuntimeError(f"fading must be disabled after the anchor for {branch.name}")
        if any(row.get("preview_commit_parity") is not True for row in branch.intervals):
            raise RuntimeError(f"preview/commit parity failed for {branch.name}")
        if branch.evidence.get("termination") not in (None, "completed"):
            raise RuntimeError(f"{branch.name} terminated before the sealed H3 horizon")
    for interval in range(H3):
        rows = [branch.intervals[interval] for branch in outcomes.values()]
        for field in ("served_users", "active_beams", "active_satellites"):
            if any(not _same(rows[0].get(field), row.get(field)) for row in rows[1:]):
                raise RuntimeError(f"{field} differs at interval {interval}")
        nonfocal = [row.get("nonfocal_actions") for row in rows]
        if any(not _same(nonfocal[0], value) for value in nonfocal[1:]):
                raise RuntimeError(f"nonfocal physical action differs at interval {interval}")
    anchor_fingerprints = {
        branch.evidence.get("anchor_fingerprint_sha256")
        for branch in outcomes.values()
    }
    if None in anchor_fingerprints or len(anchor_fingerprints) != 1:
        raise RuntimeError("four branches do not share one common anchor fingerprint")
    top = outcomes["top_gp"]
    rank = outcomes["C3-RANK-R"]
    cert = outcomes["C3-CERT-R"]
    if top.useful_bits < outcomes["reference"].useful_bits:
        raise RuntimeError("top-GP useful bits below reference")
    if rank.useful_bits < cert.useful_bits:
        raise RuntimeError("C3-RANK-R useful bits below C3-CERT-R")
    for name in ("top_gp", "C3-RANK-R", "C3-CERT-R"):
        events = outcomes[name].intervals
        reference_events = outcomes["reference"].intervals
        if int(events[0].get("phi1", 0)) != int(reference_events[0].get("phi1", 0)) + 1:
            raise RuntimeError(f"{name} does not have exactly one initial additional phi1")
        if int(events[0].get("phi2", 0)) != int(reference_events[0].get("phi2", 0)):
            raise RuntimeError(f"{name} has an unexpected initial phi2 event")
        for interval in range(1, H3):
            if int(events[interval].get("phi1", 0)) != int(reference_events[interval].get("phi1", 0)):
                raise RuntimeError(f"{name} has a later phi1 event")
            if int(events[interval].get("phi2", 0)) != int(reference_events[interval].get("phi2", 0)):
                raise RuntimeError(f"{name} has a later phi2 event")


def evaluate_postselection(
    *,
    factory: TwinFactory,
    anchor: Mapping[str, Any],
    selected_ids: Mapping[str, Any],
    evaluate_branch: Callable[[Any, Any, np.random.Generator], BranchOutcome],
    realised_rng_factory: Callable[[], np.random.Generator],
) -> dict[str, BranchOutcome]:
    """Evaluate all four branches from replayed, equal anchors.

    The callback must set fading off and preserve the untouched realised
    mobility stream.  A fresh RNG object is supplied to each branch, all with
    the same initial state, so branch execution cannot consume another branch's
    stream.  Outcomes are all retained; this function performs no outcome
    filtering.
    """

    if set(selected_ids) != {"reference", "top_gp", "C3-RANK-R", "C3-CERT-R"}:
        raise ValueError("selected_ids must contain exactly the four frozen branches")
    outcomes: dict[str, BranchOutcome] = {}
    initial_states: list[dict[str, Any]] = []
    common_fingerprint: str | None = None
    for name in ("reference", "top_gp", "C3-RANK-R", "C3-CERT-R"):
        twin = factory.replay_prefix(anchor)
        branch_fingerprint = factory.fingerprint(twin)
        if name == "reference":
            common_fingerprint = branch_fingerprint
        elif branch_fingerprint != common_fingerprint:
            raise RuntimeError("post-selection replay anchor fingerprint mismatch")
        realised_rng = realised_rng_factory()
        initial_states.append(realised_rng.bit_generator.state)
        # The callback owns the immutable fading-off setting and exact H3 loop.
        outcome = evaluate_branch(twin, selected_ids[name], realised_rng)
        if outcome.evidence.get("anchor_fingerprint_sha256") != common_fingerprint:
            raise RuntimeError("branch did not retain the common anchor fingerprint")
        outcomes[name] = outcome
    first_state = state_sha256(initial_states[0])
    if any(state_sha256(state) != first_state for state in initial_states[1:]):
        raise RuntimeError("branches do not share common initial realised RNG state")
    validate_branch_contract(outcomes)
    return outcomes


def paired_effects(outcomes: Mapping[str, BranchOutcome]) -> dict[str, float]:
    validate_branch_contract(outcomes)
    ref, top = outcomes["reference"], outcomes["top_gp"]
    rank, cert = outcomes["C3-RANK-R"], outcomes["C3-CERT-R"]
    return {
        "Delta_E_payload_ref": ref.payload_energy_j - top.payload_energy_j,
        "Delta_EE_ref": top.canonical_ee - ref.canonical_ee,
        "Delta_E_payload_cert": cert.payload_energy_j - rank.payload_energy_j,
        "Delta_EE_cert": rank.canonical_ee - cert.canonical_ee,
        "Delta_E_payload_rank": rank.payload_energy_j - top.payload_energy_j,
        "Delta_EE_rank": top.canonical_ee - rank.canonical_ee,
    }


def seed_t95(seed_means: Sequence[float]) -> float:
    """Return the frozen five-seed lower endpoint (mean minus t*sample SE)."""

    if len(seed_means) != SEED_COUNT:
        raise ValueError("seed-t95 requires exactly five defined seed means")
    values = np.asarray(seed_means, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("seed means must be finite")
    return float(values.mean() - T95 * values.std(ddof=1) / math.sqrt(SEED_COUNT))


def aggregate_effects(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate eligible anchors equally, then seed means equally."""

    rows = list(rows)
    if not rows:
        return {"eligible_anchors": 0, "support_by_seed": {}, "seed_means": {}}
    keys = tuple(k for k in rows[0] if k.startswith("Delta_"))
    by_seed: dict[Any, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_seed.setdefault(row["evaluation_seed"], []).append(row)
    seed_means: dict[Any, dict[str, float]] = {}
    for seed, seed_rows in by_seed.items():
        seed_means[seed] = {
            key: float(np.mean([float(row[key]) for row in seed_rows])) for key in keys
        }
    pooled = {key: float(np.mean([float(row[key]) for row in rows])) for key in keys}
    t95 = {
        key: seed_t95([seed_means[seed][key] for seed in by_seed])
        if len(by_seed) == SEED_COUNT
        else None
        for key in keys
    }
    return {
        "eligible_anchors": len(rows),
        "support_by_seed": {
            opaque_seed_id(seed): len(seed_rows) for seed, seed_rows in by_seed.items()
        },
        "seed_means": {
            opaque_seed_id(seed): values for seed, values in seed_means.items()
        },
        "pooled_means": pooled,
        "seed_t95_lower": t95,
    }


def stage0_decision(
    rows: Iterable[Mapping[str, Any]],
    aggregation: Mapping[str, Any],
    *,
    engineering_ok: bool,
    branch_guards_ok: bool,
    outcome_timing_leak: bool = False,
) -> str:
    """Apply the frozen terminal rule; no post-outcome guard is configurable."""

    rows = list(rows)
    if not engineering_ok or not branch_guards_ok or outcome_timing_leak:
        return CERTIFICATE_FAILURE
    support = aggregation.get("support_by_seed", {})
    pooled = aggregation.get("pooled_means", {})
    seed_means = aggregation.get("seed_means", {})
    lower = aggregation.get("seed_t95_lower", {})
    if len(support) != SEED_COUNT or any(int(value) <= 0 for value in support.values()):
        return DROP_ROLE
    if len(rows) < 20:
        return DROP_ROLE
    for row in rows:
        # A condition-valid certificate is retained even at non-positive GP.
        # The terminal rule, however, may pass only when every selected
        # deterministic/control proposal has positive GP.
        if float(row.get("gain_j", 0.0)) <= 0.0:
            return DROP_ROLE
        selected_gains = row.get("selected_gain_j", {})
        if isinstance(selected_gains, Mapping):
            for value in selected_gains.values():
                if value is None or float(value) <= 0.0:
                    return DROP_ROLE
    for metric in ("Delta_E_payload_ref", "Delta_E_payload_cert", "Delta_EE_ref", "Delta_EE_cert"):
        values = [float(seed[metric]) for seed in seed_means.values()]
        if float(pooled.get(metric, -math.inf)) <= 0.0:
            return DROP_ROLE
        if sum(value > 0.0 for value in values) < 4:
            return DROP_ROLE
        if lower.get(metric) is None or float(lower[metric]) <= 0.0:
            return DROP_ROLE
    return PASS_RESULT


def _dependency_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {"python": platform.python_version()}
    for name in ("numpy", "torch", "sgp4"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _valid_sha256(value: Any) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _frozen_tle_hashes(prereg_path: Path) -> dict[str, str]:
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    rows = prereg["sections"]["ephemeris"]["frozen_files"]
    return {str(row["file"]): str(row["sha256"]) for row in rows}


def _relative_repo_path(path: Path) -> str:
    """Canonical relative path used as a closure-manifest key."""

    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO.resolve()))
    except ValueError as exc:
        raise RuntimeError(f"closure path is outside the repository: {path}") from exc


def _required_closure_files(
    *, runner_path: Path = Path(__file__), spec_path: Path = SPEC_PATH,
    method_path: Path = METHOD_PATH,
) -> set[str]:
    """Return the exact C3 closure that must be sealed before seed reveal."""

    paths: set[Path] = {
        runner_path,
        Path(__file__).with_name("test_run_c3_stage0.py"),
        Path(__file__).with_name("run_c2_stage0.py"),
        Path(__file__).with_name("test_c2_stage0.py"),
        spec_path,
        OTHER_SPEC_PATH,
        method_path,
        SOURCE_DRIFT_MANIFEST,
        HELPER_CLOSURE_MANIFEST,
        C3_V1_HELPER,
        C3_DISJOINT_HELPER,
        ORACLE_HELPER,
        CHECKPOINT_LOADER_HELPER,
        DEFAULT_PREREG,
        DEFAULT_INPUT / "main" / "final-checkpoint.pt",
        *_default_code_paths(),
    }
    return {_relative_repo_path(path) for path in paths}


def _closure_file_map(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    files = payload.get("files")
    if not isinstance(files, Mapping) or not files:
        raise RuntimeError("closure manifest has no exact file hashes")
    for relative, digest in files.items():
        name = str(relative)
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise RuntimeError(f"closure file path is not repository-relative: {name}")
        if not _valid_sha256(digest):
            raise RuntimeError(f"closure file digest is malformed: {name}")
        target = REPO / name
        if not target.is_file() or sha256_file(target) != digest:
            raise RuntimeError(f"closure file drift: {name}")
    return files


def verify_closure_manifest(
    manifest_path: Path, *, runner_path: Path = Path(__file__),
    spec_path: Path = SPEC_PATH, method_path: Path = METHOD_PATH,
    prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path | None = None,
) -> dict[str, Any]:
    """Verify the complete C3 closure before a seed manifest is opened.

    The manifest is intentionally stricter than a handful of top-level hashes:
    every runner/test/helper/source file is listed and checked, runtime
    versions and the frozen TLE inventory are attested, and the pre-reveal
    test/disjointness attestations are explicit.  This function never opens a
    seed payload.
    """

    if not manifest_path.exists():
        raise FileNotFoundError(f"closure manifest does not exist: {manifest_path}")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("closure manifest must be canonical JSON") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != CLOSURE_SCHEMA:
        raise RuntimeError("invalid C3 Stage-0 closure-manifest schema")
    files = _closure_file_map(payload)
    expected = {
        "runner_sha256": sha256_file(runner_path),
        "test_sha256": sha256_file(Path(__file__).with_name("test_run_c3_stage0.py")),
        "spec_sha256": sha256_file(spec_path),
        "companion_spec_sha256": sha256_file(OTHER_SPEC_PATH),
        "method_sha256": sha256_file(method_path),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"closure manifest mismatch: {key}")
    required = _required_closure_files(
        runner_path=runner_path, spec_path=spec_path, method_path=method_path
    )
    missing = sorted(required - set(files))
    if missing:
        raise RuntimeError("closure manifest misses required files: " + ", ".join(missing))

    aliases = {
        "analysis_code_sha256": EXPECTED_ANALYSIS_CODE_SHA256,
        "source_drift_manifest_sha256": EXPECTED_SOURCE_DRIFT_MANIFEST_SHA256,
        "helper_closure_manifest_sha256": EXPECTED_HELPER_CLOSURE_MANIFEST_SHA256,
        "c3_v1_helper_sha256": EXPECTED_C3_V1_HELPER_SHA256,
        "oracle_helper_sha256": EXPECTED_ORACLE_HELPER_SHA256,
        "checkpoint_loader_helper_sha256": EXPECTED_CHECKPOINT_LOADER_SHA256,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
        "prereg_sha256": EXPECTED_PREREG_SHA256,
    }
    for key, expected_value in aliases.items():
        value = payload.get(key)
        if value != expected_value:
            raise RuntimeError(f"closure manifest mismatch: {key}")
    if _code_sha256(_default_code_paths()) != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("reviewed analysis source changed")

    versions = payload.get("runtime", payload.get("dependency_versions"))
    if not isinstance(versions, Mapping):
        raise RuntimeError("closure manifest omits runtime dependency versions")
    expected_versions = _dependency_versions()
    for key in ("python", "numpy", "torch", "sgp4"):
        if versions.get(key) != expected_versions.get(key):
            raise RuntimeError(f"closure dependency-version mismatch: {key}")

    attestations = payload.get("attestations")
    if not isinstance(attestations, Mapping):
        attestations = payload
    for key in (
        "tests_passed_before_seed_reveal",
        "repository_disjointness_checked_before_reveal",
    ):
        if attestations.get(key) is not True:
            raise RuntimeError(f"closure lacks pre-reveal attestation: {key}")
    receipts = payload.get("test_receipts")
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or len(receipts) < 2:
        raise RuntimeError("closure requires detailed test receipts")
    commands: list[str] = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping):
            raise RuntimeError("closure test receipt is malformed")
        if receipt.get("exit_code") != 0 or not _valid_sha256(receipt.get("stdout_sha256")):
            raise RuntimeError("closure test receipt is not a sealed pass")
        command = str(receipt.get("command", ""))
        if not command:
            raise RuntimeError("closure test receipt omits its exact command")
        commands.append(command)
    for required_test in ("test_c2_stage0.py", "test_run_c3_stage0.py"):
        if not any(required_test in command for command in commands):
            raise RuntimeError(f"closure omits explicit {required_test} execution")

    expected_tles = _frozen_tle_hashes(prereg_path)
    tle_inventory = payload.get("tle_files", payload.get("frozen_tle_files"))
    if not isinstance(tle_inventory, Mapping) or dict(tle_inventory) != expected_tles:
        raise RuntimeError("closure TLE inventory does not match frozen preregistration")
    actual_tle_root = Path(TLE_ROOT_DEFAULT).expanduser() if tle_root is None else tle_root
    for relative, expected_hash in expected_tles.items():
        target = actual_tle_root / relative
        if not target.is_file() or sha256_file(target) != expected_hash:
            raise RuntimeError(f"closure TLE drift: {relative}")

    dependencies = payload.get("dependencies")
    if dependencies is not None:
        if not isinstance(dependencies, Mapping) or not dependencies:
            raise RuntimeError("closure dependencies must be a non-empty mapping")
        for name, digest in dependencies.items():
            if name not in files or files[name] != digest:
                raise RuntimeError(f"closure dependency is not in exact file map: {name}")
    return dict(payload)


def _validate_seed_payload(payload: Mapping[str, Any], *, closure_sha256: str) -> tuple[int, ...]:
    if payload.get("schema") != SEED_SCHEMA:
        raise RuntimeError("invalid C3 Stage-0 seed-manifest schema")
    if payload.get("closure_manifest_sha256") != closure_sha256:
        raise RuntimeError("seed manifest does not bind the closure manifest")
    raw = payload.get("c3_seeds")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise RuntimeError("seed manifest must contain c3_seeds")
    if len(raw) != SEED_COUNT:
        raise RuntimeError("formal C3 campaign requires exactly five seeds")
    if any(isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) for seed in raw):
        raise RuntimeError("C3 seeds must be integer values")
    seeds = tuple(int(seed) for seed in raw)
    if len(set(seeds)) != SEED_COUNT:
        raise RuntimeError("formal C3 campaign requires five unique seeds")
    if payload.get("seed_count", SEED_COUNT) != SEED_COUNT:
        raise RuntimeError("seed manifest seed_count is not five")
    if payload.get("repository_disjointness_checked_before_reveal") is not True:
        raise RuntimeError("seed manifest lacks pre-reveal disjointness attestation")
    if not _valid_sha256(payload.get("disjointness_search_receipt_sha256")):
        raise RuntimeError("seed manifest lacks a sealed disjointness-search receipt")
    if payload.get("seed_namespace", "C3") != "C3":
        raise RuntimeError("seed manifest namespace is not C3")
    prior = payload.get("c2_seeds", payload.get("previous_seeds"))
    if prior is not None:
        if not isinstance(prior, Sequence) or isinstance(prior, (str, bytes)):
            raise RuntimeError("prior seed disjointness list is malformed")
        prior_values = [int(seed) for seed in prior]
        if len(prior_values) != len(set(prior_values)) or set(prior_values) & set(seeds):
            raise RuntimeError("C3 seeds are not disjoint from prior formal seeds")
    return seeds


def load_seed_manifest(
    seed_manifest: Path, closure_manifest: Path, *, prereg_path: Path = DEFAULT_PREREG,
    tle_root: Path | None = None,
) -> Mapping[str, Any]:
    """Verify closure first, then load exactly five opaque seed records."""

    verify_closure_manifest(
        closure_manifest, prereg_path=prereg_path, tle_root=tle_root
    )
    closure_sha = sha256_file(closure_manifest)
    if not seed_manifest.exists():
        raise FileNotFoundError(f"seed manifest does not exist: {seed_manifest}")
    payload = json.loads(seed_manifest.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RuntimeError("seed manifest must be a JSON object")
    _validate_seed_payload(payload, closure_sha256=closure_sha)
    return dict(payload)


# ---------------------------------------------------------------------------
# Frozen environment adapter
# ---------------------------------------------------------------------------


def _json_key(key: PhysicalKey | None) -> list[int] | None:
    return None if key is None else [int(key[0]), int(key[1])]


def _served_key(evaluation: Any, uid: int) -> PhysicalKey | None:
    if not bool(evaluation.resolution.served[uid]):
        return None
    return (
        int(evaluation.resolution.serving_satellite[uid]),
        int(evaluation.resolution.serving_cell[uid]),
    )


def _users_on(evaluation: Any, key: PhysicalKey) -> list[int]:
    return [
        uid
        for uid in range(len(evaluation.resolution.served))
        if _served_key(evaluation, uid) == key
    ]


def _active_keys(evaluation: Any) -> tuple[PhysicalKey, ...]:
    return tuple(sorted((int(key[0]), int(key[1])) for key in evaluation.resolution.active_beams))


def _active_satellites(evaluation: Any) -> tuple[int, ...]:
    return tuple(sorted({int(key[0]) for key in _active_keys(evaluation)}))


def _physical_actions(table: Any) -> list[tuple[int, PhysicalKey]]:
    by_key: dict[PhysicalKey, int] = {}
    for action in np.flatnonzero(table.mask).tolist():
        association = table.association(int(action))
        if not isinstance(association, Association):
            continue
        key = (int(association.norad_id), int(association.cell_id))
        by_key[key] = min(int(action), by_key.get(key, int(action)))
    return [(action, key) for key, action in sorted(by_key.items())]


def _main_actions(
    trainer: Any, states: Sequence[Any], wrapped_masks: Sequence[Any]
) -> np.ndarray:
    """Run frozen Main Q1-only masked-greedy inference."""

    encoded = trainer.encode_states(list(states))
    masks = np.stack([row.mask for row in wrapped_masks])
    q1 = trainer.scalarized_q_values(encoded, objective_weights=(1.0, 0.0, 0.0))
    return np.asarray(masked_greedy_actions(q1, masks), dtype=np.int32)


def _key_for_action(table: Any, action: int) -> PhysicalKey | None:
    if int(action) == NO_OP_ACTION:
        return None
    association = table.association(int(action))
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _action_for_key(table: Any, key: PhysicalKey | None) -> int | None:
    if key is None:
        return NO_OP_ACTION if table.num_valid == 0 else None
    matches = [
        int(action)
        for action in np.flatnonzero(table.mask).tolist()
        if int(table.norad_ids[action]) == int(key[0])
        and int(table.cell_ids[action]) == int(key[1])
    ]
    if len(matches) > 1:
        raise RuntimeError(f"duplicate physical key {key} in one slot table")
    return matches[0] if matches else None


def _unique_valid_keys(table: Any) -> tuple[PhysicalKey, ...]:
    return tuple(key for _action, key in _physical_actions(table))


def _anchor_fingerprint(
    wrapped: Any, env_rng: np.random.Generator, observation: Any
) -> tuple[dict[str, Any], str]:
    receipt = {
        "epoch": wrapped.epoch.isoformat(),
        "step_index": int(observation.step_index),
        "wrapped": _wrapped_mutable_state_receipt(wrapped),
        "environment_rng_sha256": _rng_sha(env_rng),
        "candidate_table_sha256": _object_sha(observation.candidates.slot_tables),
        "observation_state_sha256": state_sha256(observation.state_matrix),
        "observation_mask_sha256": state_sha256(observation.masks),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
    }
    return receipt, state_sha256(receipt)


def _reconstruct_anchor(
    archive: Any, *, seed: int, prefix_actions: Sequence[np.ndarray]
) -> dict[str, Any]:
    """Build a fresh wrapper and replay the physical Main prefix."""

    wrapped = checkpoint_loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    for expected_step, frozen_actions in enumerate(prefix_actions):
        if int(observation.step_index) != expected_step:
            raise RuntimeError("prefix replay step-index drift")
        result = wrapped.step(np.asarray(frozen_actions, dtype=np.int32), env_rng)
        if bool(result.done) and expected_step + 1 < len(prefix_actions):
            raise RuntimeError("prefix replay reached terminal state early")
        states, masks = result.user_states, result.action_masks
        observation = wrapped.last_outcome.observation
    receipt, digest = _anchor_fingerprint(wrapped, env_rng, observation)
    return {
        "wrapped": wrapped,
        "env_rng": env_rng,
        "states": states,
        "masks": masks,
        "observation": observation,
        "fingerprint": receipt,
        "fingerprint_sha256": digest,
        "prefix_length": len(prefix_actions),
    }


def _focal_schedule(seed: int) -> dict[int, tuple[int, ...]]:
    """Census all 100 users at every frozen anchor step."""

    del seed
    return {step: tuple(range(USERS)) for step in sorted(ANCHOR_STEPS)}


def _set_fading(wrapped: Any, enabled: bool = False) -> Any:
    original = wrapped.environment.physics
    wrapped.environment.physics = replace(original, fading_enabled=enabled)
    return original


def _preview_parity(preview: Any, outcome: Any) -> tuple[bool, str | None]:
    """Compare every preview field that can affect the C3 receipt."""

    try:
        oracle._assert_full_preview_parity(preview, outcome)
        return True, None
    except (AttributeError, RuntimeError, AssertionError) as exc:
        # Keep a local fallback because older oracle helper revisions exposed
        # only the smaller preview assertion.
        pairs = (
            (preview.resolution.served, outcome.resolution.served, "served"),
            (preview.resolution.serving_cell, outcome.resolution.serving_cell, "serving_cell"),
            (preview.resolution.serving_satellite, outcome.resolution.serving_satellite, "serving_satellite"),
            (preview.resolution.outage_infeasible, outcome.resolution.outage_infeasible, "outage_infeasible"),
        )
        for expected, observed, name in pairs:
            if not np.array_equal(expected, observed):
                return False, f"{name} mismatch: {exc}"
        if (
            preview.resolution.demand_by_beam != outcome.resolution.demand_by_beam
            or preview.resolution.eligible_load_by_beam
            != outcome.resolution.eligible_load_by_beam
        ):
            return False, f"beam-load mismatch: {exc}"
        return False, str(exc)


def _supply(power_w: float, physics: Any) -> float:
    power = np.asarray([float(power_w)], dtype=np.float64)
    efficiency = pa_efficiency(
        power,
        max_efficiency=physics.pa_max_efficiency,
        saturation_power_w=physics.pa_saturation_power_w,
    )
    return float(supply_power_w(power, efficiency)[0])


def _source_power_stats(evaluation: Any, source_key: PhysicalKey) -> tuple[float, float] | None:
    users = _users_on(evaluation, source_key)
    if len(users) < 2:
        return None
    powers = sorted((float(evaluation.link_power_w[uid]) for uid in users), reverse=True)
    return powers[0], powers[1]


def _beam_power_map(evaluation: Any) -> dict[PhysicalKey, float]:
    keys = [tuple(map(int, key)) for key in evaluation.radiating.norad_ids.tolist()]
    cells = [int(value) for value in evaluation.radiating.cell_ids.tolist()]
    powers = [float(value) for value in evaluation.radiating.power_w.tolist()]
    return {(norad, cell): power for (norad, cell), power in zip(zip(keys, cells), powers, strict=True)}


def _active_beam_power(evaluation: Any, key: PhysicalKey) -> float | None:
    return _beam_power_map(evaluation).get(key)


def _physical_key_rows(actions: np.ndarray, observation: Any) -> tuple[PhysicalKey | None, ...]:
    return physical_action_keys(actions, observation.candidates.slot_tables)


def _reference_evaluation(anchor: Mapping[str, Any], trainer: Any) -> tuple[np.ndarray, Any, tuple[PhysicalKey | None, ...]]:
    wrapped = anchor["wrapped"]
    actions = _main_actions(trainer, anchor["states"], anchor["masks"])
    original = _set_fading(wrapped, False)
    try:
        evaluation = wrapped.environment.evaluate_actions(actions, np.random.default_rng(0))
    finally:
        wrapped.environment.physics = original
    return actions, evaluation, _physical_key_rows(actions, anchor["observation"])


def _source_qualification(
    anchor: Mapping[str, Any], trainer: Any, *, focal_user: int,
    baseline_actions: np.ndarray, baseline: Any,
    baseline_keys: Sequence[PhysicalKey | None],
) -> tuple[dict[str, Any], tuple[PhysicalKey, ...]]:
    """Apply the frozen continuing-incumbent/current-slot source filter."""

    wrapped = anchor["wrapped"]
    observation = anchor["observation"]
    source = baseline_keys[focal_user]
    row: dict[str, Any] = {
        "focal_user": int(focal_user),
        "reference_action": int(baseline_actions[focal_user]),
        "reference_key": _json_key(source),
        "reference_handover": baseline.handovers[focal_user].value,
    }
    if source is None or not bool(baseline.resolution.served[focal_user]):
        return row | {"status": "ineligible", "reason": "reference_unserved"}, ()
    previous = wrapped.environment._previous_association[focal_user]
    segment = wrapped.environment._segments[focal_user]
    continuing = bool(
        isinstance(previous, Association)
        and segment is not None
        and (int(previous.norad_id), int(previous.cell_id)) == source
        and segment.continues(previous)
    )
    if not continuing or baseline.handovers[focal_user] is not HandoverClass.NONE:
        return row | {
            "status": "ineligible",
            "reason": "reference_not_continuing_incumbent",
        }, ()
    source_users = _users_on(baseline, source)
    if len(source_users) < 2:
        return row | {"status": "ineligible", "reason": "source_load_lt_2"}, ()
    other = [uid for uid in source_users if uid != focal_user]
    source_max = float(baseline.link_power_w[focal_user])
    source_next = max(float(baseline.link_power_w[uid]) for uid in other)
    if not source_max > source_next + STRICT_MAX_TOLERANCE_W:
        return row | {
            "status": "ineligible",
            "reason": "focal_not_strict_unique_source_max",
            "source_load": len(source_users),
            "source_max_power_w": source_max,
            "source_next_power_w": source_next,
        }, ()
    active = set(_active_keys(baseline))
    table = observation.candidates.slot_tables[focal_user]
    candidates = tuple(
        key for _action, key in _physical_actions(table)
        if key != source and key[0] == source[0] and key in active
    )
    row |= {
        "status": "source_qualified" if candidates else "ineligible",
        "reason": "candidate_scan_required" if candidates else "no_active_same_satellite_destination",
        "source_load": len(source_users),
        "source_max_power_w": source_max,
        "source_next_power_w": source_next,
        "candidate_count_pre_certificate": len(candidates),
    }
    return row, candidates


def _hard_safe_candidates(
    anchor: Mapping[str, Any], *, focal_user: int, source_key: PhysicalKey,
    baseline_actions: np.ndarray, baseline: Any,
    candidate_keys: Sequence[PhysicalKey],
) -> tuple[list[dict[str, Any]], list[PhysicalKey]]:
    """Build the broader current-slot support used by C3-CERT-R.

    This pass is pre-outcome and one-slot only.  It does not inspect forecast
    or realised future streams, so a candidate remains in the control support
    even when its later H3 result is poor.
    """

    wrapped = anchor["wrapped"]
    observation = anchor["observation"]
    source_stats = _source_power_stats(baseline, source_key)
    if source_stats is None:
        raise RuntimeError("hard-safe scan received a source with fewer than two users")
    source_max, source_next = source_stats
    active = set(_active_keys(baseline))
    source_users = set(_users_on(baseline, source_key))
    rows: list[dict[str, Any]] = []
    safe: list[PhysicalKey] = []
    seen: set[PhysicalKey] = set()
    for key in candidate_keys:
        key = (int(key[0]), int(key[1]))
        if key in seen:
            continue
        seen.add(key)
        checks: dict[str, Any] = {
            "candidate_key": _json_key(key),
            "same_satellite": key[0] == source_key[0],
            "different_source": key != source_key,
            "destination_active": key in active,
        }
        candidate_action = _action_for_key(observation.candidates.slot_tables[focal_user], key)
        checks["remapped_action"] = candidate_action
        if candidate_action is None:
            checks["candidate_valid"] = False
            checks["reason"] = "candidate_physical_id_unmappable"
            rows.append(checks)
            continue
        alternative_actions = baseline_actions.copy()
        alternative_actions[focal_user] = int(candidate_action)
        original = _set_fading(wrapped, False)
        try:
            alternative = wrapped.environment.evaluate_actions(
                alternative_actions, np.random.default_rng(0)
            )
        finally:
            wrapped.environment.physics = original
        destination_users = _users_on(baseline, key)
        destination_max = (
            max(float(baseline.link_power_w[uid]) for uid in destination_users)
            if destination_users else None
        )
        candidate_power = float(alternative.link_power_w[focal_user])
        source_alt_users = _users_on(alternative, source_key)
        source_alt_max = (
            max(float(alternative.link_power_w[uid]) for uid in source_alt_users)
            if source_alt_users else None
        )
        predicted = _supply(source_next, wrapped.environment.physics) - _supply(
            source_max, wrapped.environment.physics
        )
        realised = float(alternative.system_power_w - baseline.system_power_w)
        nonfocal_same = all(
            _key_for_action(observation.candidates.slot_tables[uid], int(alternative_actions[uid]))
            == baseline_keys_key
            for uid, baseline_keys_key in enumerate(
                physical_action_keys(baseline_actions, observation.candidates.slot_tables)
            )
            if uid != focal_user
        )
        served_same = np.array_equal(alternative.resolution.served, baseline.resolution.served)
        active_same = set(_active_keys(alternative)) == active
        destination_unchanged = (
            destination_max is not None
            and candidate_power <= destination_max + POWER_TOLERANCE_W
        )
        conditions = {
            "same_satellite": checks["same_satellite"],
            "different_source": checks["different_source"],
            "destination_active": checks["destination_active"],
            "candidate_valid": bool(alternative.resolution.served[focal_user]),
            "candidate_intra_satellite": alternative.handovers[focal_user] is HandoverClass.INTRA_SATELLITE,
            "served_set_same": served_same,
            "active_sets_same": active_same
            and set(_active_satellites(alternative)) == set(_active_satellites(baseline)),
            "nonfocal_actions_same": nonfocal_same,
            "destination_max_unchanged": destination_unchanged,
            "source_relief": source_alt_max is not None and source_alt_max < source_max - POWER_TOLERANCE_W,
            "power_lower": realised < -POWER_TOLERANCE_W,
            "pa_identity": abs(realised - predicted) <= POWER_TOLERANCE_W,
        }
        checks |= {
            "conditions": conditions,
            "source_max_power_w": source_max,
            "source_next_power_w": source_next,
            "source_after_max_power_w": source_alt_max,
            "destination_max_power_w": destination_max,
            "candidate_power_w": candidate_power,
            "predicted_delta_system_power_w": predicted,
            "realised_delta_system_power_w": realised,
            "identity_residual_w": realised - predicted,
            "served_users": np.flatnonzero(alternative.resolution.served).tolist(),
            "active_beams": [_json_key(key) for key in _active_keys(alternative)],
            "active_satellites": list(_active_satellites(alternative)),
            "nonfocal_physical_actions": [
                _json_key(value)
                for uid, value in enumerate(physical_action_keys(alternative_actions, observation.candidates.slot_tables))
                if uid != focal_user
            ],
        }
        failed = [name for name, passed in conditions.items() if not passed]
        checks["hard_safe"] = not failed
        checks["reasons"] = failed
        rows.append(checks)
        if not failed:
            safe.append(key)
    return rows, safe


def _forecast_candidate(
    archive: Any, trainer: Any, *, seed: int, prefix_actions: Sequence[np.ndarray],
    step_index: int, focal_user: int, source_key: PhysicalKey,
    candidate_key: PhysicalKey,
) -> CertificateResult:
    """Run the sealed three-interval independent forecast certificate."""

    reference = _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
    candidate = _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
    if reference["fingerprint_sha256"] != candidate["fingerprint_sha256"]:
        return CertificateResult(
            candidate_id=candidate_key,
            certified=False,
            reasons=("anchor_fingerprint_mismatch",),
            gain_j=None,
            intervals=(),
            evidence={"anchor_fingerprint_sha256": reference["fingerprint_sha256"]},
        )

    forecast_reference = derive_rng(
        NAMESPACES["forecast"], EXPECTED_CHECKPOINT_SHA256, seed, step_index, focal_user
    )
    forecast_candidate = derive_rng(
        NAMESPACES["forecast"], EXPECTED_CHECKPOINT_SHA256, seed, step_index, focal_user
    )
    actual_mobility_hash = _rng_sha(reference["wrapped"].environment._mobility_rng)
    forecast_hash = _rng_sha(forecast_reference)
    independence = {
        "forecast_rng_objects_distinct": forecast_reference is not forecast_candidate,
        "forecast_rng_initial_state_equal": _rng_sha(forecast_reference) == _rng_sha(forecast_candidate),
        "forecast_not_actual_mobility_object": forecast_reference is not reference["wrapped"].environment._mobility_rng,
        "forecast_state_differs_from_actual_mobility": forecast_hash != actual_mobility_hash,
        "forecast_rng_sha256": forecast_hash,
        "actual_mobility_rng_sha256": actual_mobility_hash,
    }
    if not all(independence.values()):
        return CertificateResult(
            candidate_id=candidate_key,
            certified=False,
            reasons=("forecast_rng_independence_failure",),
            gain_j=None,
            intervals=(),
            forecast_objects_distinct=False,
            forecast_initial_state_sha256=forecast_hash,
            evidence={
                "anchor_fingerprint_sha256": reference["fingerprint_sha256"],
                "forecast_rng_independence": independence,
            },
        )

    for branch, forecast in ((reference, forecast_reference), (candidate, forecast_candidate)):
        environment = branch["wrapped"].environment
        environment._mobility_rng = copy.deepcopy(forecast)
        environment.physics = replace(environment.physics, fading_enabled=False)
        # Fading is off, but a separate environment stream is retained and
        # recorded so no branch can accidentally share a mutable RNG object.
        branch["env_rng"] = np.random.default_rng(0)

    reasons: list[str] = []
    intervals: list[dict[str, Any]] = []
    gain = 0.0
    ref_states, ref_masks, ref_observation = reference["states"], reference["masks"], reference["observation"]
    cand_states, cand_masks, cand_observation = candidate["states"], candidate["masks"], candidate["observation"]
    for offset in range(H3):
        ref_actions = _main_actions(trainer, ref_states, ref_masks)
        cand_actions = _main_actions(trainer, cand_states, cand_masks)
        ref_table = ref_observation.candidates.slot_tables[focal_user]
        cand_table = cand_observation.candidates.slot_tables[focal_user]
        source_action = _action_for_key(ref_table, source_key)
        candidate_action = _action_for_key(cand_table, candidate_key)
        if source_action is None:
            reasons.append("reference_hold_invalid")
        else:
            ref_actions[focal_user] = source_action
        if candidate_action is None:
            reasons.append("candidate_hold_invalid")
        else:
            cand_actions[focal_user] = candidate_action
        ref_keys = _physical_key_rows(ref_actions, ref_observation)
        cand_keys = _physical_key_rows(cand_actions, cand_observation)
        if tuple(key for uid, key in enumerate(ref_keys) if uid != focal_user) != tuple(
            key for uid, key in enumerate(cand_keys) if uid != focal_user
        ):
            reasons.append("nonfocal_action_mismatch")

        ref_env = reference["wrapped"].environment
        cand_env = candidate["wrapped"].environment
        ref_preview = ref_env.evaluate_actions(ref_actions, reference["env_rng"])
        cand_preview = cand_env.evaluate_actions(cand_actions, candidate["env_rng"])
        ref_result = reference["wrapped"].step(ref_actions, reference["env_rng"])
        cand_result = candidate["wrapped"].step(cand_actions, candidate["env_rng"])
        ref_outcome = reference["wrapped"].last_outcome
        cand_outcome = candidate["wrapped"].last_outcome
        ref_parity, ref_parity_error = _preview_parity(ref_preview, ref_outcome)
        cand_parity, cand_parity_error = _preview_parity(cand_preview, cand_outcome)
        if not ref_parity or not cand_parity:
            reasons.append("preview_commit_parity_failure")

        ref_source_stats = _source_power_stats(ref_outcome, source_key)
        cand_source_users = _users_on(cand_outcome, source_key)
        cand_source_max = (
            max(float(cand_outcome.link_power_w[uid]) for uid in cand_source_users)
            if cand_source_users else None
        )
        ref_destination_users = _users_on(ref_outcome, candidate_key)
        destination_max = (
            max(float(ref_outcome.link_power_w[uid]) for uid in ref_destination_users)
            if ref_destination_users else None
        )
        ref_max = ref_source_stats[0] if ref_source_stats else None
        ref_next = ref_source_stats[1] if ref_source_stats else None
        predicted = (
            _supply(ref_next, ref_env.physics) - _supply(ref_max, ref_env.physics)
            if ref_max is not None and ref_next is not None else math.nan
        )
        realised = float(cand_outcome.system_power_w - ref_outcome.system_power_w)
        residual = realised - predicted
        served_same = np.array_equal(ref_outcome.resolution.served, cand_outcome.resolution.served)
        active_same = (
            _active_keys(ref_outcome) == _active_keys(cand_outcome)
            and _active_satellites(ref_outcome) == _active_satellites(cand_outcome)
        )
        conditions = {
            "reference_hold_valid": _served_key(ref_outcome, focal_user) == source_key,
            "candidate_hold_valid": _served_key(cand_outcome, focal_user) == candidate_key,
            "candidate_service": bool(cand_outcome.resolution.served[focal_user]),
            "served_set_same": served_same,
            "active_sets_same": active_same,
            "destination_max_unchanged": destination_max is not None
            and float(cand_outcome.link_power_w[focal_user]) <= destination_max + POWER_TOLERANCE_W,
            "source_relief": cand_source_max is not None and ref_max is not None
            and cand_source_max < ref_max - POWER_TOLERANCE_W,
            "candidate_power_lower": float(cand_outcome.system_power_w)
            < float(ref_outcome.system_power_w) - POWER_TOLERANCE_W,
            "pa_identity": math.isfinite(residual) and abs(residual) <= POWER_TOLERANCE_W,
        }
        reasons.extend(name for name, passed in conditions.items() if not passed)
        ref_phi1 = int(ref_outcome.handovers[focal_user] is HandoverClass.INTRA_SATELLITE)
        cand_phi1 = int(cand_outcome.handovers[focal_user] is HandoverClass.INTRA_SATELLITE)
        ref_phi2 = int(ref_outcome.handovers[focal_user] is HandoverClass.INTER_SATELLITE)
        cand_phi2 = int(cand_outcome.handovers[focal_user] is HandoverClass.INTER_SATELLITE)
        if offset == 0:
            if cand_phi1 - ref_phi1 != 1:
                reasons.append("initial_phi1_count_not_exactly_one_additional")
            if cand_phi2 != ref_phi2:
                reasons.append("initial_phi2_changed")
        else:
            if cand_phi1 != ref_phi1:
                reasons.append("later_phi1_event")
            if cand_phi2 != ref_phi2:
                reasons.append("later_phi2_event")
        intervals.append({
            "interval": offset,
            "reference_physical_actions": [_json_key(key) for key in ref_keys],
            "candidate_physical_actions": [_json_key(key) for key in cand_keys],
            "nonfocal_actions": [_json_key(key) for uid, key in enumerate(ref_keys) if uid != focal_user],
            "reference_action_indices": np.asarray(ref_actions, dtype=np.int32).tolist(),
            "candidate_action_indices": np.asarray(cand_actions, dtype=np.int32).tolist(),
            "served_users": np.flatnonzero(ref_outcome.resolution.served).tolist(),
            "active_beams": [_json_key(key) for key in _active_keys(ref_outcome)],
            "active_satellites": list(_active_satellites(ref_outcome)),
            "reference_system_power_w": float(ref_outcome.system_power_w),
            "candidate_system_power_w": float(cand_outcome.system_power_w),
            "source_max_power_w": ref_max,
            "source_next_power_w": ref_next,
            "destination_max_power_w": destination_max,
            "predicted_delta_system_power_w": predicted,
            "realised_delta_system_power_w": realised,
            "identity_residual_w": residual,
            "reference_focal_power_w": float(ref_outcome.link_power_w[focal_user]),
            "candidate_focal_power_w": float(cand_outcome.link_power_w[focal_user]),
            "reference_handover": ref_outcome.handovers[focal_user].value,
            "candidate_handover": cand_outcome.handovers[focal_user].value,
            "phi1": cand_phi1,
            "phi2": cand_phi2,
            "fading_enabled": False,
            "preview_commit_parity": bool(ref_parity and cand_parity),
            "preview_commit_parity_error": {"reference": ref_parity_error, "candidate": cand_parity_error},
            "remapping": {
                "source_key": _json_key(source_key),
                "candidate_key": _json_key(candidate_key),
                "reference_action": source_action,
                "candidate_action": candidate_action,
            },
            "rng": {
                "reference_environment_before": _rng_sha(reference["env_rng"]),
                "candidate_environment_before": _rng_sha(candidate["env_rng"]),
                "reference_mobility_after": _rng_sha(ref_env._mobility_rng),
                "candidate_mobility_after": _rng_sha(cand_env._mobility_rng),
            },
            "conditions": conditions,
            "termination": "completed" if not ref_result.done and not cand_result.done else "episode_end",
        })
        gain += DELTA_S * (float(ref_outcome.system_power_w) - float(cand_outcome.system_power_w))
        ref_states, ref_masks, ref_observation = ref_result.user_states, ref_result.action_masks, ref_outcome.observation
        cand_states, cand_masks, cand_observation = cand_result.user_states, cand_result.action_masks, cand_outcome.observation

    evidence = {
        "anchor_fingerprint_sha256": reference["fingerprint_sha256"],
        "forecast_rng_independence": independence,
        "forecast_final_state_sha256": [_rng_sha(forecast_reference), _rng_sha(forecast_candidate)],
        "conditions_1_to_8_only": True,
        "termination": "completed",
    }
    unique_reasons = tuple(dict.fromkeys(reasons))
    return CertificateResult(
        candidate_id=candidate_key,
        certified=not unique_reasons and math.isfinite(gain),
        reasons=unique_reasons,
        gain_j=float(gain) if math.isfinite(gain) else None,
        intervals=tuple(intervals),
        forecast_objects_distinct=True,
        forecast_initial_state_sha256=_rng_sha(forecast_reference),
        forecast_final_state_sha256=(_rng_sha(forecast_reference), _rng_sha(forecast_candidate)),
        evidence=evidence,
    )


def _branch_interval_row(
    *, branch: Mapping[str, Any], outcome: Any, actions: np.ndarray,
    observation: Any, preview_passed: bool, preview_error: str | None,
    focal_user: int, target_key: PhysicalKey | None, mapped_action: int | None,
    reference_outcome: Any | None = None,
) -> dict[str, Any]:
    keys = _physical_key_rows(actions, observation)
    environment = branch["wrapped"].environment
    rng_after = {
        "environment_rng_sha256": _rng_sha(branch["env_rng"]),
        "mobility_rng_sha256": _rng_sha(environment._mobility_rng),
        "age_rng_sha256": _rng_sha(environment._age_rng),
    }
    # The no-focal evaluation is computed by the caller at this same
    # pre-decision state.  It is retained only as an explanatory diagnostic;
    # it is not a reward and never enters selection or the terminal rule.
    focal_marginal = float(
        outcome.system_power_w - float(branch.get("no_focal_system_power_w", math.nan))
    )
    row: dict[str, Any] = {
        "interval": int(outcome.step_index),
        "physical_actions": [_json_key(key) for key in keys],
        "action_indices": np.asarray(actions, dtype=np.int32).tolist(),
        "served_users": np.flatnonzero(outcome.resolution.served).tolist(),
        "served_count": int(outcome.resolution.served_count),
        "active_beams": [_json_key(key) for key in _active_keys(outcome)],
        "active_satellites": list(_active_satellites(outcome)),
        "link_power_w": np.asarray(outcome.link_power_w, dtype=np.float64).tolist(),
        "link_rate_bps": np.asarray(outcome.link_rate_bps, dtype=np.float64).tolist(),
        "throughput_bps": float(outcome.energy.system_throughput_bps),
        "system_power_w": float(outcome.system_power_w),
        "fixed_power_w": float(outcome.fixed_power_w),
        "canonical_ee_bits_per_j": float(outcome.energy.system_ee_bits_per_j),
        "focal_marginal_power_w": focal_marginal,
        "focal_served": bool(outcome.resolution.served[focal_user]),
        "focal_action_key": _json_key(keys[focal_user]),
        "focal_handover": outcome.handovers[focal_user].value,
        "phi1": int(outcome.handovers[focal_user] is HandoverClass.INTRA_SATELLITE),
        "phi2": int(outcome.handovers[focal_user] is HandoverClass.INTER_SATELLITE),
        "fading_enabled": False,
        "preview_commit_parity": bool(preview_passed),
        "preview_commit_parity_error": preview_error,
        "remapping": {
            "target_physical_key": _json_key(target_key),
            "mapped_action": mapped_action,
            "executed_physical_key": _json_key(keys[focal_user]),
        },
        "rng": {
            "environment_before_sha256": branch.get("rng_before", {}).get("environment_rng_sha256"),
            "mobility_before_sha256": branch.get("rng_before", {}).get("mobility_rng_sha256"),
            "age_before_sha256": branch.get("rng_before", {}).get("age_rng_sha256"),
            **rng_after,
        },
        "termination": "episode_end" if bool(outcome.done) else "continuing",
    }
    if reference_outcome is not None:
        ref_source = _active_beam_power(reference_outcome, target_key) if target_key is not None else None
        row["reference_system_power_w"] = float(reference_outcome.system_power_w)
        row["system_power_delta_vs_reference_w"] = float(outcome.system_power_w - reference_outcome.system_power_w)
        row["reference_target_max_power_w"] = ref_source
    return row


def _window_metrics(rows: Sequence[Mapping[str, Any]], *, focal_user: int) -> dict[str, Any]:
    if len(rows) != H3:
        raise RuntimeError("C3 horizon must contain exactly H3 intervals")
    bits = DELTA_S * sum(float(row["throughput_bps"]) for row in rows)
    energy = DELTA_S * sum(float(row["system_power_w"]) for row in rows)
    if not math.isfinite(bits) or not math.isfinite(energy) or energy <= 0.0:
        raise RuntimeError("C3 branch has non-positive/non-finite payload energy")
    focal_service = all(bool(row["focal_served"]) for row in rows)
    return {
        "intervals": len(rows),
        "useful_bits": float(bits),
        "payload_energy_j": float(energy),
        "canonical_ee": float(bits / energy),
        "mean_system_power_w": float(statistics.fmean(float(row["system_power_w"]) for row in rows)),
        "focal_marginal_power_w": [float(row["focal_marginal_power_w"]) for row in rows],
        "focal_marginal_power_mean_w": float(statistics.fmean(float(row["focal_marginal_power_w"]) for row in rows)),
        "focal_served_all": focal_service,
        "served_fraction": float(statistics.fmean(float(row["served_count"]) / USERS for row in rows)),
        "phi1": int(sum(int(row["phi1"]) for row in rows)),
        "phi2": int(sum(int(row["phi2"]) for row in rows)),
        "focal_user": int(focal_user),
        "active_beams": [row["active_beams"] for row in rows],
        "active_satellites": [row["active_satellites"] for row in rows],
    }


def _run_actual_branches(
    archive: Any, trainer: Any, *, seed: int, prefix_actions: Sequence[np.ndarray],
    focal_user: int, choices: Mapping[str, PhysicalKey],
) -> dict[str, Any]:
    """Replay four selected branches from one common realised anchor."""

    required = ("reference", "top_gp", "C3-RANK-R", "C3-CERT-R")
    if set(choices) != set(required):
        raise ValueError("C3 requires exactly reference/top_gp/C3-RANK-R/C3-CERT-R")
    branches = {
        name: _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
        for name in required
    }
    fingerprints = {branch["fingerprint_sha256"] for branch in branches.values()}
    failures: list[str] = []
    if len(fingerprints) != 1:
        failures.append("anchor_fingerprint_mismatch")
    common_fingerprint = next(iter(fingerprints), None)
    initial_env_rng = {
        name: _rng_sha(branch["env_rng"]) for name, branch in branches.items()
    }
    if len(set(initial_env_rng.values())) != 1:
        failures.append("realised_rng_initial_state_mismatch")
    for branch in branches.values():
        branch["wrapped"].environment.physics = replace(
            branch["wrapped"].environment.physics, fading_enabled=False
        )
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in required}
    option_open = {name: True for name in required}
    terminations: dict[str, list[dict[str, Any]]] = {name: [] for name in required}
    nonfocal_receipts: list[dict[str, Any]] = []

    for offset in range(H3):
        action_rows: dict[str, np.ndarray] = {}
        key_rows: dict[str, tuple[PhysicalKey | None, ...]] = {}
        maps: dict[str, dict[str, Any]] = {}
        for name in required:
            branch = branches[name]
            actions = _main_actions(trainer, branch["states"], branch["masks"])
            observation = branch["observation"]
            target = choices[name]
            mapped = None
            if option_open[name]:
                mapped = _action_for_key(observation.candidates.slot_tables[focal_user], target)
                if mapped is None:
                    option_open[name] = False
                    terminations[name].append({"interval": offset, "reason": "bound_physical_id_invalid"})
                    failures.append(f"remapping_failure_{name}_interval_{offset}")
                else:
                    actions[focal_user] = int(mapped)
            action_rows[name] = actions
            key_rows[name] = _physical_key_rows(actions, observation)
            maps[name] = {
                "target_physical_key": _json_key(target),
                "mapped_action": mapped,
                "option_open": bool(option_open[name]),
                "executed_physical_key": _json_key(key_rows[name][focal_user]),
                "released": False,
            }
            branch["rng_before"] = {
                "environment_rng_sha256": _rng_sha(branch["env_rng"]),
                "mobility_rng_sha256": _rng_sha(branch["wrapped"].environment._mobility_rng),
                "age_rng_sha256": _rng_sha(branch["wrapped"].environment._age_rng),
            }
        reference_nonfocal = tuple(
            key for uid, key in enumerate(key_rows["reference"]) if uid != focal_user
        )
        equal = True
        for name in required:
            value = tuple(key for uid, key in enumerate(key_rows[name]) if uid != focal_user)
            if value != reference_nonfocal:
                equal = False
                failures.append(f"nonfocal_physical_action_divergence_interval_{offset}_{name}")
        nonfocal_receipts.append({
            "interval": offset,
            "equal": equal,
            "physical_actions_by_branch": {
                name: [_json_key(key) for uid, key in enumerate(key_rows[name]) if uid != focal_user]
                for name in required
            },
        })

        for name in required:
            branch = branches[name]
            pre_observation = branch["observation"]
            no_focal_actions = np.asarray(action_rows[name], dtype=np.int32).copy()
            no_focal_actions[focal_user] = NO_OP_ACTION
            no_focal_preview = branch["wrapped"].environment.evaluate_actions(
                no_focal_actions, branch["env_rng"]
            )
            branch["no_focal_system_power_w"] = float(no_focal_preview.system_power_w)
            preview = branch["wrapped"].environment.evaluate_actions(
                action_rows[name], branch["env_rng"]
            )
            result = branch["wrapped"].step(action_rows[name], branch["env_rng"])
            outcome = branch["wrapped"].last_outcome
            parity, parity_error = _preview_parity(preview, outcome)
            if not parity:
                failures.append(f"preview_commit_parity_{name}_interval_{offset}")
            row = _branch_interval_row(
                branch=branch,
                outcome=outcome,
                actions=action_rows[name],
                observation=pre_observation,
                preview_passed=parity,
                preview_error=parity_error,
                focal_user=focal_user,
                target_key=choices[name],
                mapped_action=maps[name]["mapped_action"],
                reference_outcome=(
                    branches["reference"].get("last_outcome")
                    if name != "reference" else None
                ),
            )
            row["horizon_interval"] = offset
            # Keep the outcome available until all same-slot branch rows have
            # been emitted, without exposing an environment snapshot API.
            branch["last_outcome"] = outcome
            rows[name].append(row)
            branch["states"], branch["masks"] = result.user_states, result.action_masks
            branch["observation"] = outcome.observation
            if bool(result.done) and offset + 1 < H3:
                failures.append(f"early_termination_{name}_interval_{offset}")
                terminations[name].append({"interval": offset, "reason": "episode_end"})

        # Recompute per-branch reference deltas now that all outcomes for this
        # interval exist.  This avoids order-dependent state reads above.
        ref_row = rows["reference"][-1]
        for name in required[1:]:
            row = rows[name][-1]
            row["reference_system_power_w"] = ref_row["system_power_w"]
            row["system_power_delta_vs_reference_w"] = row["system_power_w"] - ref_row["system_power_w"]
            reference_outcome = branches["reference"]["last_outcome"]
            candidate_outcome = branches[name]["last_outcome"]
            source_stats = _source_power_stats(reference_outcome, choices["reference"])
            if source_stats is None:
                row["pa_identity"] = False
                failures.append(f"pa_recurrence_evidence_missing_{name}_interval_{offset}")
            else:
                source_max, source_next = source_stats
                predicted = _supply(
                    source_next, branches["reference"]["wrapped"].environment.physics
                ) - _supply(
                    source_max, branches["reference"]["wrapped"].environment.physics
                )
                realised = float(
                    candidate_outcome.system_power_w - reference_outcome.system_power_w
                )
                residual = realised - predicted
                row.update({
                    "source_max_power_w": source_max,
                    "source_next_power_w": source_next,
                    "predicted_delta_system_power_w": predicted,
                    "realised_delta_system_power_w": realised,
                    "identity_residual_w": residual,
                    "pa_identity": bool(abs(residual) <= POWER_TOLERANCE_W),
                })
                if not row["pa_identity"]:
                    failures.append(f"pa_identity_{name}_interval_{offset}")

    metrics: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, BranchOutcome] = {}
    for name in required:
        if len(rows[name]) != H3:
            failures.append(f"branch_horizon_length_{name}")
            continue
        window = _window_metrics(rows[name], focal_user=focal_user)
        service = bool(window["focal_served_all"])
        evidence = {
            "anchor_fingerprint_sha256": common_fingerprint,
            "branch_fingerprint_sha256": branches[name]["fingerprint_sha256"],
            "termination": "completed" if not terminations[name] else "terminated",
            "fading_enabled": False,
            "realised_rng_initial_sha256": initial_env_rng[name],
            "realised_rng_final_sha256": _rng_sha(branches[name]["env_rng"]),
            "mobility_rng_final_sha256": _rng_sha(branches[name]["wrapped"].environment._mobility_rng),
            "age_rng_final_sha256": _rng_sha(branches[name]["wrapped"].environment._age_rng),
        }
        metrics[name] = window
        outcomes[name] = BranchOutcome(
            name=name,
            useful_bits=float(window["useful_bits"]),
            payload_energy_j=float(window["payload_energy_j"]),
            canonical_ee=float(window["canonical_ee"]),
            service=service,
            intervals=tuple(rows[name]),
            evidence=evidence,
        )
    branch_guards_ok = False
    effects: dict[str, float] = {}
    if set(outcomes) == set(required):
        try:
            validate_branch_contract(outcomes)
            effects = paired_effects(outcomes)
            branch_guards_ok = not failures
        except (RuntimeError, ValueError) as exc:
            failures.append(f"branch_contract:{exc}")
    return {
        "anchor_fingerprint_sha256": common_fingerprint,
        "anchor_fingerprint": branches["reference"]["fingerprint"] if branches else None,
        "branch_fingerprint_sha256": {
            name: branch["fingerprint_sha256"] for name, branch in branches.items()
        },
        "realised_rng_initial_sha256": initial_env_rng,
        "engineering_failures": sorted(set(failures)),
        "branch_guards_ok": branch_guards_ok,
        "nonfocal_equality": nonfocal_receipts,
        "option_terminations": terminations,
        "metrics": metrics,
        "intervals": rows,
        "outcomes": outcomes,
        "effects": effects,
    }


def _anchor_row(
    archive: Any, trainer: Any, *, seed: int, step_index: int,
    focal_user: int, prefix_actions: Sequence[np.ndarray],
) -> dict[str, Any]:
    """Census one focal user and retain all pre/post-selection evidence."""

    anchor = _reconstruct_anchor(archive, seed=seed, prefix_actions=prefix_actions)
    baseline_actions, baseline, baseline_keys = _reference_evaluation(anchor, trainer)
    base: dict[str, Any] = {
        "evaluation_seed": int(seed),
        "step_index": int(step_index),
        "focal_user": int(focal_user),
        "anchor_fingerprint_sha256": anchor["fingerprint_sha256"],
        "anchor_fingerprint": anchor["fingerprint"],
        "reference_action_indices": np.asarray(baseline_actions, dtype=np.int32).tolist(),
        "reference_physical_actions": [_json_key(key) for key in baseline_keys],
        "anchor_rng": {
            "environment_rng_sha256": _rng_sha(anchor["env_rng"]),
            "mobility_rng_sha256": _rng_sha(anchor["wrapped"].environment._mobility_rng),
            "age_rng_sha256": _rng_sha(anchor["wrapped"].environment._age_rng),
        },
    }
    source_row, candidate_keys = _source_qualification(
        anchor, trainer, focal_user=focal_user, baseline_actions=baseline_actions,
        baseline=baseline, baseline_keys=baseline_keys,
    )
    base["source_qualification"] = source_row
    if source_row.get("status") != "source_qualified":
        return base | {"status": "ineligible", "reason": source_row.get("reason", "source_ineligible")}
    source_key = baseline_keys[focal_user]
    assert source_key is not None
    hard_safe_rows, hard_safe_keys = _hard_safe_candidates(
        anchor, focal_user=focal_user, source_key=source_key,
        baseline_actions=baseline_actions, baseline=baseline,
        candidate_keys=candidate_keys,
    )
    base["hard_safe_candidates"] = hard_safe_rows
    base["hard_safe_keys"] = [_json_key(key) for key in hard_safe_keys]
    if not hard_safe_keys:
        return base | {"status": "ineligible", "reason": "no_current_slot_hard_safe_candidate"}

    certificates = [
        _forecast_candidate(
            archive, trainer, seed=seed, prefix_actions=prefix_actions,
            step_index=step_index, focal_user=focal_user,
            source_key=source_key, candidate_key=key,
        )
        for key in hard_safe_keys
    ]
    certificate_rows = []
    for result in certificates:
        certificate_rows.append({
            "candidate_key": _json_key(result.candidate_id),
            "certified": bool(result.certified),
            "reasons": list(result.reasons),
            "gain_j": result.gain_j,
            "intervals": list(result.intervals),
            "evidence": dict(result.evidence),
        })
    base["certificates"] = certificate_rows
    top = select_top_gain(certificates)
    if top is None:
        return base | {
            "status": "ineligible",
            "reason": "no_h3_certified_candidate",
            "certified_candidate_count": 0,
        }
    rank_rng = derive_rng(
        NAMESPACES["rank_control"], EXPECTED_CHECKPOINT_SHA256, seed, step_index, focal_user
    )
    cert_rng = derive_rng(
        NAMESPACES["cert_control"], EXPECTED_CHECKPOINT_SHA256, seed, step_index, focal_user
    )
    certified = [result for result in certificates if result.certified]
    rank_key = select_rank_control(certificates, rank_rng)
    cert_key = select_certificate_control(hard_safe_keys, cert_rng)
    selected = {
        "reference": source_key,
        "top_gp": tuple(int(value) for value in top.candidate_id),
        "C3-RANK-R": tuple(int(value) for value in rank_key),
        "C3-CERT-R": tuple(int(value) for value in cert_key),
    }
    actual = _run_actual_branches(
        archive, trainer, seed=seed, prefix_actions=prefix_actions,
        focal_user=focal_user, choices=selected,
    )
    selected_gain: dict[str, float | None] = {
        "top_gp": top.gain_j,
        "C3-RANK-R": None,
        "C3-CERT-R": None,
    }
    for result in certificates:
        if result.candidate_id == rank_key:
            selected_gain["C3-RANK-R"] = result.gain_j
        if result.candidate_id == cert_key:
            selected_gain["C3-CERT-R"] = result.gain_j
    branch_effects = actual.get("effects", {})
    row = base | {
        "status": "evaluated",
        "source_key": _json_key(source_key),
        "selected": {name: _json_key(key) for name, key in selected.items()},
        "selected_gain_j": selected_gain,
        "selected_top_gp": _json_key(top.candidate_id),
        "selected_rank_control": _json_key(rank_key),
        "selected_certificate_control": _json_key(cert_key),
        "rng_derivations": {
            "rank_control_initial_sha256": _rng_sha(rank_rng),
            "certificate_control_initial_sha256": _rng_sha(cert_rng),
            "rank_control_selected_support": len(certified),
            "certificate_control_selected_support": len(hard_safe_keys),
        },
        "actual": actual,
    }
    row.update(branch_effects)
    row["gain_j"] = top.gain_j
    row["branch_guards_ok"] = bool(actual.get("branch_guards_ok", False))
    row["engineering_failures"] = list(actual.get("engineering_failures", ()))
    return row


def _run_seed(archive: Any, trainer: Any, *, seed: int) -> dict[str, Any]:
    """Run exactly one frozen 10-interval Main episode and census anchors."""

    wrapped = checkpoint_loader._make_environment(archive, users=USERS)
    env_rng, mobility_rng, _action_rng, _control_rng = _evaluation_rngs(seed)
    states, masks, observation = wrapped.reset(env_rng, mobility_rng)
    schedule = _focal_schedule(seed)
    prefix_actions: list[np.ndarray] = []
    anchors: list[dict[str, Any]] = []
    baseline_steps: list[dict[str, Any]] = []
    rollout_failures: list[dict[str, Any]] = []
    while True:
        step_index = int(observation.step_index)
        actions = _main_actions(trainer, states, masks)
        before = {
            "environment_rng_sha256": _rng_sha(env_rng),
            "mobility_rng_sha256": _rng_sha(wrapped.environment._mobility_rng),
            "age_rng_sha256": _rng_sha(wrapped.environment._age_rng),
        }
        baseline_preview = wrapped.environment.evaluate_actions(actions, env_rng)
        if step_index in ANCHOR_STEPS:
            for focal_user in schedule[step_index]:
                try:
                    anchor = _anchor_row(
                        archive, trainer, seed=seed, step_index=step_index,
                        focal_user=focal_user, prefix_actions=prefix_actions,
                    )
                except Exception as exc:  # the terminal rule treats this as engineering failure
                    anchor = {
                        "evaluation_seed": int(seed),
                        "step_index": step_index,
                        "focal_user": int(focal_user),
                        "status": "engineering_failure",
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                anchors.append(anchor)
        prefix_actions.append(actions.copy())
        result = wrapped.step(actions, env_rng)
        outcome = wrapped.last_outcome
        parity, parity_error = _preview_parity(baseline_preview, outcome)
        if not parity:
            rollout_failures.append({
                "step_index": step_index,
                "failure": f"baseline_preview_commit_parity:{parity_error}",
            })
        baseline_steps.append({
            "step_index": step_index,
            "physical_actions": [_json_key(key) for key in _physical_key_rows(actions, observation)],
            "action_indices": np.asarray(actions, dtype=np.int32).tolist(),
            "served_users": np.flatnonzero(outcome.resolution.served).tolist(),
            "active_beams": [_json_key(key) for key in _active_keys(outcome)],
            "active_satellites": list(_active_satellites(outcome)),
            "system_power_w": float(outcome.system_power_w),
            "throughput_bps": float(outcome.energy.system_throughput_bps),
            "canonical_ee": float(outcome.energy.system_ee_bits_per_j),
            "preview_commit_parity": parity,
            "preview_commit_parity_error": parity_error,
            "rng_before": before,
            "rng_after": {
                "environment_rng_sha256": _rng_sha(env_rng),
                "mobility_rng_sha256": _rng_sha(wrapped.environment._mobility_rng),
                "age_rng_sha256": _rng_sha(wrapped.environment._age_rng),
            },
        })
        if bool(result.done):
            break
        states, masks = result.user_states, result.action_masks
        observation = outcome.observation
    return {
        "evaluation_seed": int(seed),
        "focal_schedule": {str(step): list(users) for step, users in schedule.items()},
        "baseline_steps": baseline_steps,
        "engineering_failures": rollout_failures,
        "anchors": anchors,
    }


def _aggregate_rollouts(rollouts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [
        dict(row)
        for rollout in rollouts
        for row in rollout.get("anchors", ())
        if row.get("status") == "evaluated"
    ]
    engineering_failures = [
        {
            "evaluation_seed": rollout.get("evaluation_seed"),
            "step_index": failure.get("step_index"),
            "focal_user": None,
            "failures": [failure.get("failure")],
        }
        for rollout in rollouts
        for failure in rollout.get("engineering_failures", ())
    ] + [
        {
            "evaluation_seed": row.get("evaluation_seed"),
            "step_index": row.get("step_index"),
            "focal_user": row.get("focal_user"),
            "failures": list(row.get("engineering_failures", ())),
        }
        for rollout in rollouts
        for row in rollout.get("anchors", ())
        if row.get("status") == "engineering_failure"
        or row.get("engineering_failures")
    ]
    aggregation = aggregate_effects(rows)
    # No eligible proposal is a statistical zero-support result, not an
    # engineering failure.  Guard checks become material only for evaluated
    # rows.
    branch_guards_ok = all(bool(row.get("branch_guards_ok")) for row in rows)
    engineering_ok = not engineering_failures and all(
        not row.get("engineering_failures") for row in rows
    )
    decision = stage0_decision(
        rows, aggregation, engineering_ok=engineering_ok,
        branch_guards_ok=branch_guards_ok,
    )
    return {
        "sampled_anchors": sum(len(rollout.get("anchors", ())) for rollout in rollouts),
        "eligible_anchors": len(rows),
        "engineering_failures": engineering_failures,
        "branch_guards_ok": branch_guards_ok,
        "engineering_ok": engineering_ok,
        "aggregation": aggregation,
        "decision": decision,
    }


def _runtime_receipt() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: importlib.metadata.version(name)
            if importlib.metadata.packages_distributions().get(name)
            else None
            for name in ("numpy", "torch", "sgp4")
        },
    }


def _redact_seed_values(value: Any, *, key: str | None = None) -> Any:
    """Remove raw evaluation seeds from a result while retaining lineage."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for name, child in value.items():
            if name == "evaluation_seed":
                result[name] = opaque_seed_id(child)
            else:
                result[name] = _redact_seed_values(child, key=str(name))
        return result
    if isinstance(value, (list, tuple)):
        return [_redact_seed_values(child, key=key) for child in value]
    return value


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    parser.add_argument(
        "--tle-root", type=Path, default=Path(TLE_ROOT_DEFAULT).expanduser()
    )
    parser.add_argument("--seed-manifest", type=Path, required=True)
    parser.add_argument("--closure-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _arguments(argv)
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite output: {args.output}")
    if sha256_file(SPEC_PATH) != EXPECTED_SPEC_SHA256:
        raise RuntimeError("Stage-0 specification digest changed")
    if sha256_file(OTHER_SPEC_PATH) != EXPECTED_COMPANION_SPEC_SHA256:
        raise RuntimeError("companion Stage-0 specification digest changed")
    if sha256_file(METHOD_PATH) != EXPECTED_METHOD_SHA256:
        raise RuntimeError("v0.4 method digest changed")
    if sha256_file(args.prereg) != EXPECTED_PREREG_SHA256:
        raise RuntimeError("frozen preregistration changed")
    if _code_sha256(_default_code_paths()) != EXPECTED_ANALYSIS_CODE_SHA256:
        raise RuntimeError("reviewed analysis source changed")
    closure = verify_closure_manifest(
        args.closure_manifest,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
    )
    # Closure verification is deliberately complete before this call.  It is
    # the only point that opens the sealed seed values, and no raw seed is
    # copied into the result bundle.
    seed_payload = load_seed_manifest(
        args.seed_manifest,
        args.closure_manifest,
        prereg_path=args.prereg,
        tle_root=args.tle_root,
    )
    seeds = tuple(int(seed) for seed in seed_payload["c3_seeds"])
    record = read_prereg(args.prereg)
    closure_sha = sha256_file(args.closure_manifest)

    with tempfile.TemporaryDirectory(prefix="mcrl-c3-stage0-") as temporary:
        archive = checkpoint_loader._frozen_archive(
            record, args.tle_root, Path(temporary) / "frozen-tle"
        )
        trainer, checkpoint = checkpoint_loader._verify_and_load_trainer(
            record, archive, run_dir=args.input_dir / "main", users=USERS
        )
        if checkpoint.get("checkpoint_sha256") != EXPECTED_CHECKPOINT_SHA256:
            raise RuntimeError("corrected Main checkpoint changed")
        rollouts = [_run_seed(archive, trainer, seed=seed) for seed in seeds]

    aggregate = _aggregate_rollouts(rollouts)
    output = {
        "schema": OUTPUT_SCHEMA,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "claim_boundary": (
            "legacy-geometry, fading-off, non-training C3 paired Stage-0 evidence "
            "only; no Q2/Q3 learnability, Main transfer, actual-fading, carrier, "
            "training, effectiveness, joint-benefit, or novelty claim"
        ),
        "inputs": {
            "method_sha256": sha256_file(METHOD_PATH),
            "spec_sha256": sha256_file(SPEC_PATH),
            "companion_spec_sha256": sha256_file(OTHER_SPEC_PATH),
            "runner_sha256": sha256_file(Path(__file__).resolve()),
            "test_sha256": sha256_file(Path(__file__).with_name("test_run_c3_stage0.py")),
            "closure_manifest_sha256": closure_sha,
            "seed_manifest_sha256": sha256_file(args.seed_manifest),
            "checkpoint_sha256": checkpoint["checkpoint_sha256"],
            "prereg_sha256": sha256_file(args.prereg),
            "analysis_code_sha256": _code_sha256(_default_code_paths()),
            "closure_schema": closure["schema"],
        },
        "runtime": _runtime_receipt(),
        "seed_ids": [opaque_seed_id(seed) for seed in seeds],
        "rollouts": _redact_seed_values(rollouts),
        "aggregate": _redact_seed_values(aggregate),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    staged = args.output.with_name(args.output.name + ".tmp")
    if staged.exists():
        raise FileExistsError(f"refusing to overwrite staged output: {staged}")
    staged.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    try:
        os.link(staged, args.output)
    except FileExistsError as exc:
        raise FileExistsError(f"refusing to overwrite output: {args.output}") from exc
    finally:
        staged.unlink(missing_ok=True)
    print(json.dumps({"output": str(args.output), "decision": aggregate["decision"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
