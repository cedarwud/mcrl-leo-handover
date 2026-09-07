"""Fail-closed operational seam for the reward-aligned C3 H3 certificate.

The H3 certificate is deliberately kept behind a small backend protocol.  The
adapter owns the parts that are easy to get subtly wrong at the runtime seam:

* a pre-outcome anchor is replayed into two fresh branches;
* both forecast streams are independently constructed from the domain-derived
  ``FORECAST-v2`` seed, with equal initial state but distinct RNG objects;
* each branch must return complete physical-ID, service, load, power, and
  event evidence for exactly three intervals; and
* only then is the result converted to the pure C3 core's
  :class:`ForecastInterval` and :func:`certify_candidate`.

This module does not connect C3 to Main, select a candidate, inspect a
realised outcome, or implement the retired power-primary/unique-max rule.
``roll_forward`` is intentionally a pre-outcome forecast protocol.  A real
``TrainerEnvironment`` integration can implement this protocol later without
changing the pure certificate or weakening its fail-closed guards.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping, Protocol, Sequence

import numpy as np


def _load_core() -> Any:
    """Load the sealed pure core when this scratch module is run directly."""

    try:
        import c3_reward_aligned_core as core  # type: ignore

        return core
    except ModuleNotFoundError:
        core_path = (
            Path(__file__).resolve().parent.parent
            / "catfish-stage0"
            / "c3_reward_aligned_core.py"
        )
        spec = importlib.util.spec_from_file_location(
            "c3_reward_aligned_core", core_path
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load C3 pure core: {core_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module


core = _load_core()

CandidateEvidence = core.CandidateEvidence
DECISION_INTERVAL_S = core.DECISION_INTERVAL_S
EventClass = core.EventClass
ForecastInterval = core.ForecastInterval
PhysicalId = core.PhysicalId
PowerSnapshot = core.PowerSnapshot
certify_candidate = core.certify_candidate
make_domain_rng = core.make_domain_rng
validate_candidate_pair = core.validate_candidate_pair
validate_event_class = core.validate_event_class
validate_nonfocal_action_map = core.validate_nonfocal_action_map
validate_physical_id = core.validate_physical_id


H3_INTERVALS = 3
FORECAST_NAMESPACE = "SMC-ER-C3-FORECAST-v2"
ADAPTER_SCHEMA = "smc-er-c3-h3-runtime-adapter-v1"
_SHA256_HEX = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class PreOutcomeAnchor:
    """Immutable identity for a forecast start before any candidate outcome.

    ``prefix_actions`` is retained as a copied, immutable tuple so a backend
    can replay the canonical prefix.  No realised outcome is part of this
    object or accepted by the adapter.  ``expected_anchor_fingerprint_sha256``
    is an independently recorded digest of the authoritative pre-outcome
    anchor state.  It is deliberately separate from ``checkpoint_sha256``:
    the checkpoint digest is a checkpoint/RNG authority and cannot stand in
    for the replayed anchor-state digest.
    """

    checkpoint_sha256: str
    expected_anchor_fingerprint_sha256: str
    evaluation_seed: int
    step_index: int
    focal_user_id: int
    source_id: PhysicalId
    prefix_actions: tuple[tuple[int, ...], ...] = ()


@dataclass(frozen=True)
class ForecastFrame:
    """One pre-outcome branch forecast returned by an H3 backend.

    The frame is intentionally richer than the pure core input.  In
    particular, ``focal_action`` lets the adapter prove that a physical
    commitment survived relative-slot remapping before it constructs the
    pure ``ForecastInterval``.  ``nonfocal_actions`` must contain every user
    except the focal user, including explicit ``None`` for an unserved user.
    """

    focal_action: PhysicalId | None
    nonfocal_actions: Mapping[int, PhysicalId | None]
    served_users: tuple[int, ...]
    active_beams: tuple[PhysicalId, ...]
    active_satellites: tuple[int, ...]
    loads: Mapping[PhysicalId, int]
    r3_total: int
    power: PowerSnapshot
    event: EventClass
    hold_valid: bool = True
    service: bool = True


class H3RuntimeBackend(Protocol):
    """Backend required by the adapter; no realised-outcome method exists."""

    def replay_prefix(self, anchor: PreOutcomeAnchor) -> Any:
        """Construct a fresh branch by replaying the frozen prefix."""

    def fingerprint(self, branch: Any) -> str:
        """Return the SHA-256 fingerprint of the pre-outcome branch anchor."""

    def roll_forward(
        self,
        branch: Any,
        focal_physical_id: PhysicalId,
        interval: int,
        forecast_rng: np.random.Generator,
    ) -> ForecastFrame | Mapping[str, Any]:
        """Forecast one interval without receiving a realised environment RNG."""


@dataclass(frozen=True)
class H3AdapterReceipt:
    """Auditable result of one candidate's H3 operational attempt."""

    schema: str
    status: str
    candidate_id: PhysicalId | None
    source_id: PhysicalId | None
    anchor_fingerprint_sha256: str | None
    candidate_evidence: CandidateEvidence | None
    intervals: tuple[ForecastInterval, ...]
    reasons: tuple[str, ...]
    replayed_fresh_branches: bool
    forecast_rng_objects_distinct: bool
    forecast_initial_state_sha256: tuple[str, str]
    forecast_final_state_sha256: tuple[str, str]
    nonfocal_equality_by_interval: tuple[bool, ...]

    @property
    def certified(self) -> bool:
        """Whether the pure core found nested hard-safe joint support."""

        return bool(
            self.status == "PASS"
            and self.candidate_evidence is not None
            and self.candidate_evidence.joint
        )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in _SHA256_HEX for character in value)
    )


def _canonical_json(value: Any) -> bytes:
    def default(item: Any) -> Any:
        if isinstance(item, np.ndarray):
            return item.tolist()
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError(f"cannot serialize {type(item).__name__}")

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=default,
    ).encode("utf-8")


def rng_state_sha256(rng: np.random.Generator) -> str:
    """Hash one RNG state for receipts without exposing mutable state."""

    if not isinstance(rng, np.random.Generator):
        raise ValueError("forecast RNG must be a numpy Generator")
    return hashlib.sha256(_canonical_json(rng.bit_generator.state)).hexdigest()


def _failure_receipt(
    *,
    candidate_id: PhysicalId | None,
    source_id: PhysicalId | None,
    reasons: Sequence[str],
    anchor_fingerprint_sha256: str | None = None,
    replayed_fresh_branches: bool = False,
    forecast_rng_objects_distinct: bool = False,
    forecast_initial_state_sha256: tuple[str, str] = ("", ""),
    forecast_final_state_sha256: tuple[str, str] = ("", ""),
    nonfocal_equality_by_interval: Sequence[bool] = (),
) -> H3AdapterReceipt:
    """Build a receipt that can never be mistaken for a route authorisation."""

    unique_reasons = tuple(dict.fromkeys(str(reason) for reason in reasons))
    return H3AdapterReceipt(
        schema=ADAPTER_SCHEMA,
        status="FAIL_CLOSED",
        candidate_id=candidate_id,
        source_id=source_id,
        anchor_fingerprint_sha256=anchor_fingerprint_sha256,
        candidate_evidence=None,
        intervals=(),
        reasons=unique_reasons or ("unknown_adapter_failure",),
        replayed_fresh_branches=bool(replayed_fresh_branches),
        forecast_rng_objects_distinct=bool(forecast_rng_objects_distinct),
        forecast_initial_state_sha256=forecast_initial_state_sha256,
        forecast_final_state_sha256=forecast_final_state_sha256,
        nonfocal_equality_by_interval=tuple(bool(value) for value in nonfocal_equality_by_interval),
    )


def _validate_anchor(anchor: object, *, expected_user_count: int) -> PreOutcomeAnchor:
    if type(anchor) is not PreOutcomeAnchor:
        raise ValueError("anchor must be a PreOutcomeAnchor")
    if not _is_sha256(anchor.checkpoint_sha256):
        raise ValueError("anchor checkpoint authority must be a lowercase SHA-256 hex digest")
    if not _is_sha256(anchor.expected_anchor_fingerprint_sha256):
        raise ValueError(
            "anchor expected state authority must be a lowercase SHA-256 hex digest"
        )
    if anchor.expected_anchor_fingerprint_sha256 == anchor.checkpoint_sha256:
        raise ValueError(
            "checkpoint hash cannot be used as the anchor state fingerprint"
        )
    if type(anchor.evaluation_seed) is not int or anchor.evaluation_seed < 0:
        raise ValueError("anchor evaluation seed must be a nonnegative exact integer")
    if type(anchor.step_index) is not int or anchor.step_index < 0:
        raise ValueError("anchor step index must be a nonnegative exact integer")
    if type(anchor.focal_user_id) is not int or anchor.focal_user_id < 0:
        raise ValueError("anchor focal user ID must be a nonnegative exact integer")
    if anchor.focal_user_id >= expected_user_count:
        raise ValueError("anchor focal user ID is outside the expected user range")
    validate_physical_id(anchor.source_id, field="anchor source physical ID")
    if type(anchor.prefix_actions) is not tuple:
        raise ValueError("anchor prefix actions must be an immutable tuple")
    for prefix_index, actions in enumerate(anchor.prefix_actions):
        if type(actions) is not tuple:
            raise ValueError(f"anchor prefix actions h{prefix_index} must be a tuple")
        for action in actions:
            if type(action) is not int:
                raise ValueError("anchor prefix action indices must be exact integers")
    return anchor


def _coerce_frame(raw: object) -> ForecastFrame:
    if isinstance(raw, ForecastFrame):
        return raw
    if not isinstance(raw, Mapping):
        raise ValueError("backend forecast frame must be ForecastFrame or mapping")
    required = {
        "focal_action",
        "nonfocal_actions",
        "served_users",
        "active_beams",
        "active_satellites",
        "loads",
        "r3_total",
        "power",
        "event",
    }
    missing = sorted(required - set(raw))
    if missing:
        raise ValueError(f"forecast frame is missing fields: {','.join(missing)}")
    return ForecastFrame(
        focal_action=raw["focal_action"],
        nonfocal_actions=raw["nonfocal_actions"],
        served_users=raw["served_users"],
        active_beams=raw["active_beams"],
        active_satellites=raw["active_satellites"],
        loads=raw["loads"],
        r3_total=raw["r3_total"],
        power=raw["power"],
        event=raw["event"],
        hold_valid=raw.get("hold_valid", True),
        service=raw.get("service", True),
    )


def _validate_unique_user_tuple(
    values: object,
    *,
    field: str,
    expected_user_count: int,
) -> tuple[int, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    result: list[int] = []
    for user in values:
        if type(user) is not int or user < 0 or user >= expected_user_count:
            raise ValueError(f"{field} contains an out-of-range exact user ID")
        result.append(user)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate user IDs")
    return tuple(result)


def _validate_unique_physical_tuple(
    values: object, *, field: str
) -> tuple[PhysicalId, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    result = tuple(validate_physical_id(value, field=field) for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate physical IDs")
    return result


def _validate_satellite_tuple(values: object, *, field: str) -> tuple[int, ...]:
    if not isinstance(values, tuple):
        raise ValueError(f"{field} must be a tuple")
    result: list[int] = []
    for satellite in values:
        if type(satellite) is not int or satellite < 0:
            raise ValueError(f"{field} contains an invalid satellite ID")
        result.append(satellite)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicate satellite IDs")
    return tuple(result)


def _validate_load_map(value: object) -> dict[PhysicalId, int]:
    if not isinstance(value, Mapping):
        raise ValueError("forecast eligible loads must be a mapping")
    result: dict[PhysicalId, int] = {}
    for raw_key, raw_load in value.items():
        key = validate_physical_id(raw_key, field="forecast load physical ID")
        if type(raw_load) is not int or raw_load < 0:
            raise ValueError("forecast loads must be nonnegative exact integers")
        if raw_load:
            result[key] = raw_load
    return result


def _validate_frame(
    frame: ForecastFrame,
    *,
    expected_focal_id: PhysicalId,
    focal_user_id: int,
    expected_user_count: int,
) -> ForecastFrame:
    if type(frame) is not ForecastFrame:
        raise ValueError("backend forecast frame is malformed")
    if frame.focal_action is None:
        raise ValueError("forecast frame focal physical ID is missing")
    focal_action = validate_physical_id(
        frame.focal_action, field="forecast focal physical ID"
    )
    if focal_action != expected_focal_id:
        raise ValueError("forecast focal physical ID does not match the commitment")
    validate_nonfocal_action_map(
        frame.nonfocal_actions,
        focal_user_id=focal_user_id,
        expected_user_count=expected_user_count,
    )
    _validate_unique_user_tuple(
        frame.served_users,
        field="forecast served-user set",
        expected_user_count=expected_user_count,
    )
    _validate_unique_physical_tuple(
        frame.active_beams, field="forecast active-beam set"
    )
    _validate_satellite_tuple(
        frame.active_satellites, field="forecast active-satellite set"
    )
    loads = _validate_load_map(frame.loads)
    if type(frame.r3_total) is not int:
        raise ValueError("forecast R3 total must be an exact integer")
    if type(frame.power) is not PowerSnapshot:
        raise ValueError("forecast power must be a PowerSnapshot")
    validate_event_class(frame.event)
    if type(frame.hold_valid) is not bool:
        raise ValueError("forecast hold-valid flag must be an exact boolean")
    if type(frame.service) is not bool:
        raise ValueError("forecast service flag must be an exact boolean")
    return ForecastFrame(
        focal_action=focal_action,
        nonfocal_actions=dict(frame.nonfocal_actions),
        served_users=tuple(frame.served_users),
        active_beams=tuple(frame.active_beams),
        active_satellites=tuple(frame.active_satellites),
        loads=loads,
        r3_total=frame.r3_total,
        power=frame.power,
        event=frame.event,
        hold_valid=frame.hold_valid,
        service=frame.service,
    )


def _to_interval(
    reference: ForecastFrame, candidate: ForecastFrame
) -> tuple[ForecastInterval, bool]:
    """Convert two validated frames and expose non-focal equality explicitly."""

    nonfocal_equal = reference.nonfocal_actions == candidate.nonfocal_actions
    interval = ForecastInterval(
        reference_loads=reference.loads,
        candidate_loads=candidate.loads,
        reference_r3_total=reference.r3_total,
        candidate_r3_total=candidate.r3_total,
        reference_power=reference.power,
        candidate_power=candidate.power,
        reference_nonfocal_actions=reference.nonfocal_actions,
        candidate_nonfocal_actions=candidate.nonfocal_actions,
        reference_event=reference.event,
        candidate_event=candidate.event,
        reference_hold_valid=reference.hold_valid,
        candidate_hold_valid=candidate.hold_valid,
        reference_service=reference.service,
        candidate_service=candidate.service,
        reference_served_users=reference.served_users,
        candidate_served_users=candidate.served_users,
        reference_active_beams=reference.active_beams,
        candidate_active_beams=candidate.active_beams,
        reference_active_satellites=reference.active_satellites,
        candidate_active_satellites=candidate.active_satellites,
        hidden_fallback=False,
    )
    return interval, nonfocal_equal


def certify_h3_candidate(
    backend: H3RuntimeBackend,
    *,
    anchor: PreOutcomeAnchor,
    candidate_id: PhysicalId,
    expected_user_count: int = 100,
    decision_interval_s: float = DECISION_INTERVAL_S,
) -> H3AdapterReceipt:
    """Run the operational H3 seam and delegate support semantics to pure core.

    Structural/runtime failures return ``FAIL_CLOSED`` and no evidence.  A
    complete forecast whose hard-safe, load, power, or event layer rejects the
    candidate returns ``REJECT`` together with the pure-core evidence.  Both
    states are non-authorising; only ``PASS`` with ``candidate_evidence.joint``
    is a certificate pass.
    """

    source_id: PhysicalId | None = None
    candidate_physical_id: PhysicalId | None = None
    reference_fingerprint: str | None = None
    try:
        if type(expected_user_count) is not int or expected_user_count < 1:
            raise ValueError("expected user count must be a positive exact integer")
        checked_anchor = _validate_anchor(
            anchor, expected_user_count=expected_user_count
        )
        source_id, candidate_physical_id = validate_candidate_pair(
            checked_anchor.source_id, candidate_id
        )
        # The protocol is structural and intentionally not runtime-checkable;
        # verify its three public seams explicitly.
        for name in ("replay_prefix", "fingerprint", "roll_forward"):
            if not callable(getattr(backend, name, None)):
                raise ValueError(f"backend is missing callable {name}")

        reference_branch = backend.replay_prefix(checked_anchor)
        candidate_branch = backend.replay_prefix(checked_anchor)
        if reference_branch is candidate_branch:
            return _failure_receipt(
                candidate_id=candidate_physical_id,
                source_id=source_id,
                reasons=("fresh_branch_objects_not_distinct",),
                replayed_fresh_branches=False,
            )

        reference_fingerprint = backend.fingerprint(reference_branch)
        candidate_fingerprint = backend.fingerprint(candidate_branch)
        if not _is_sha256(reference_fingerprint) or not _is_sha256(candidate_fingerprint):
            raise ValueError("anchor fingerprint must be a lowercase SHA-256 hex digest")
        fingerprint_reasons: list[str] = []
        if reference_fingerprint != candidate_fingerprint:
            fingerprint_reasons.append("anchor_fingerprint_mismatch")
        if reference_fingerprint != checked_anchor.expected_anchor_fingerprint_sha256:
            fingerprint_reasons.append("anchor_fingerprint_not_bound_to_authority")
        if candidate_fingerprint != checked_anchor.expected_anchor_fingerprint_sha256:
            fingerprint_reasons.append("candidate_fingerprint_not_bound_to_authority")
        if fingerprint_reasons:
            return _failure_receipt(
                candidate_id=candidate_physical_id,
                source_id=source_id,
                reasons=fingerprint_reasons,
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
            )

        forecast_reference = make_domain_rng(
            FORECAST_NAMESPACE,
            checked_anchor.checkpoint_sha256,
            checked_anchor.evaluation_seed,
            checked_anchor.step_index,
            checked_anchor.focal_user_id,
        )
        forecast_candidate = make_domain_rng(
            FORECAST_NAMESPACE,
            checked_anchor.checkpoint_sha256,
            checked_anchor.evaluation_seed,
            checked_anchor.step_index,
            checked_anchor.focal_user_id,
        )
        initial_rng_hashes = (
            rng_state_sha256(forecast_reference),
            rng_state_sha256(forecast_candidate),
        )
        distinct_rngs = forecast_reference is not forecast_candidate
        if not distinct_rngs or initial_rng_hashes[0] != initial_rng_hashes[1]:
            return _failure_receipt(
                candidate_id=candidate_physical_id,
                source_id=source_id,
                reasons=("forecast_rng_independence_failure",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
                forecast_rng_objects_distinct=distinct_rngs,
                forecast_initial_state_sha256=initial_rng_hashes,
            )

        intervals: list[ForecastInterval] = []
        nonfocal_equal: list[bool] = []
        for interval in range(H3_INTERVALS):
            raw_reference = backend.roll_forward(
                reference_branch,
                source_id,
                interval,
                forecast_reference,
            )
            raw_candidate = backend.roll_forward(
                candidate_branch,
                candidate_physical_id,
                interval,
                forecast_candidate,
            )
            interval_rng_hashes = (
                rng_state_sha256(forecast_reference),
                rng_state_sha256(forecast_candidate),
            )
            if interval_rng_hashes[0] != interval_rng_hashes[1]:
                return _failure_receipt(
                    candidate_id=candidate_physical_id,
                    source_id=source_id,
                    reasons=(f"forecast_rng_state_mismatch_h{interval}",),
                    anchor_fingerprint_sha256=reference_fingerprint,
                    replayed_fresh_branches=True,
                    forecast_rng_objects_distinct=True,
                    forecast_initial_state_sha256=initial_rng_hashes,
                    forecast_final_state_sha256=interval_rng_hashes,
                    nonfocal_equality_by_interval=nonfocal_equal,
                )
            reference_frame = _validate_frame(
                _coerce_frame(raw_reference),
                expected_focal_id=source_id,
                focal_user_id=checked_anchor.focal_user_id,
                expected_user_count=expected_user_count,
            )
            candidate_frame = _validate_frame(
                _coerce_frame(raw_candidate),
                expected_focal_id=candidate_physical_id,
                focal_user_id=checked_anchor.focal_user_id,
                expected_user_count=expected_user_count,
            )
            row, equal = _to_interval(reference_frame, candidate_frame)
            intervals.append(row)
            nonfocal_equal.append(equal)

        evidence = certify_candidate(
            source_id=source_id,
            candidate_id=candidate_physical_id,
            intervals=tuple(intervals),
            focal_user_id=checked_anchor.focal_user_id,
            expected_user_count=expected_user_count,
            decision_interval_s=decision_interval_s,
        )
        status = "PASS" if evidence.joint else "REJECT"
        return H3AdapterReceipt(
            schema=ADAPTER_SCHEMA,
            status=status,
            candidate_id=candidate_physical_id,
            source_id=source_id,
            anchor_fingerprint_sha256=reference_fingerprint,
            candidate_evidence=evidence,
            intervals=tuple(intervals),
            reasons=evidence.reasons,
            replayed_fresh_branches=True,
            forecast_rng_objects_distinct=True,
            forecast_initial_state_sha256=initial_rng_hashes,
            forecast_final_state_sha256=(
                rng_state_sha256(forecast_reference),
                rng_state_sha256(forecast_candidate),
            ),
            nonfocal_equality_by_interval=tuple(nonfocal_equal),
        )
    except Exception as exc:  # every adapter/runtime failure is fail-closed
        return _failure_receipt(
            candidate_id=candidate_physical_id,
            source_id=source_id,
            reasons=(f"{type(exc).__name__}:{exc}",),
            anchor_fingerprint_sha256=reference_fingerprint,
        )


__all__ = [
    "ADAPTER_SCHEMA",
    "CandidateEvidence",
    "EventClass",
    "ForecastFrame",
    "ForecastInterval",
    "H3AdapterReceipt",
    "H3RuntimeBackend",
    "PreOutcomeAnchor",
    "PowerSnapshot",
    "certify_h3_candidate",
    "rng_state_sha256",
]
