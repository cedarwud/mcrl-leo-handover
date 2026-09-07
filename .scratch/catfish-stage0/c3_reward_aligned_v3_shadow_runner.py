"""Development-only C3 V3 candidate-support shadow runner.

This module is the smallest operational seam between the canonical C3 V3
core/adapter and a later short-EP runner.  A backend supplies two fresh
pre-outcome branches, a checkpoint-backed scalarized-Main decision, and four
complete step receipts.  The runner then projects the *canonical* load/r3 and
complete-power fields and composes one fail-closed certificate.

The module deliberately has no learner, replay-buffer, routing, seed census,
outcome selection, or training code.  ``replay_prefix`` below means only the
backend's construction of a fresh deep twin from an anchor; it is not an
experience-replay operation.  The returned receipt is an engineering shadow
receipt, never a Main-consumer authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from numbers import Real
from pathlib import Path
import sys
from typing import Any, Mapping, Protocol, Sequence


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

import c3_reward_aligned_v3_core as core  # noqa: E402
import c3_reward_aligned_v3_runtime_adapter as adapter  # noqa: E402


SHADOW_SCHEMA = "smc-er-c3-v3-candidate-support-shadow-v2"
CLAIM_CEILING = (
    "development shadow only; no formal seed result, scientific efficacy, "
    "Main routing, deployment, or training authorization"
)
CERTIFICATE_OFFSETS = tuple(range(core.CERTIFICATE_STEPS))


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class C3V3ShadowAnchor:
    """Checkpoint/seed/physical-ID identity for one pre-outcome anchor."""

    checkpoint_sha256: str
    expected_anchor_fingerprint_sha256: str
    evaluation_seed: int
    step_index: int
    focal_user_id: int
    source_id: core.PhysicalId
    prefix_actions: tuple[tuple[int, ...], ...] = ()


def _validate_anchor(anchor: object, *, expected_user_count: int) -> C3V3ShadowAnchor:
    """Validate the adapter anchor without allowing a local authority copy."""

    if type(anchor) is not C3V3ShadowAnchor:
        raise ValueError("anchor must be the canonical C3V3ShadowAnchor")
    if not _is_sha256(anchor.checkpoint_sha256):
        raise ValueError("anchor checkpoint authority must be a lowercase SHA-256 digest")
    if not _is_sha256(anchor.expected_anchor_fingerprint_sha256):
        raise ValueError("anchor fingerprint authority must be a lowercase SHA-256 digest")
    if anchor.expected_anchor_fingerprint_sha256 == anchor.checkpoint_sha256:
        raise ValueError("checkpoint hash cannot stand in for anchor fingerprint")
    if type(anchor.evaluation_seed) is not int or anchor.evaluation_seed < 0:
        raise ValueError("anchor evaluation seed must be a nonnegative exact integer")
    if type(anchor.step_index) is not int or anchor.step_index < 0:
        raise ValueError("anchor step index must be a nonnegative exact integer")
    if type(anchor.focal_user_id) is not int or not 0 <= anchor.focal_user_id < expected_user_count:
        raise ValueError("anchor focal user is outside the expected user range")
    core.validate_physical_id(anchor.source_id, field="anchor source physical ID")
    if type(anchor.prefix_actions) is not tuple:
        raise ValueError("anchor prefix actions must be an immutable tuple")
    for actions in anchor.prefix_actions:
        if type(actions) is not tuple or any(type(action) is not int for action in actions):
            raise ValueError("anchor prefix actions must be tuples of exact integers")
    return anchor


@dataclass(frozen=True)
class ShadowStep:
    """One complete pre-outcome step supplied by a canonical backend.

    ``evaluation`` must be the canonical action evaluation object consumed by
    :func:`adapter.canonical_load_projection` and
    :func:`adapter.canonical_power_projection`.  The remaining fields are
    observations that the environment must expose for every user; no value is
    reconstructed from a post-hoc objective or a payload-only surrogate.
    """

    evaluation: Any
    focal_action: core.PhysicalId | None
    nonfocal_actions: Mapping[int, core.PhysicalAction]
    useful_bits: float
    reentry: tuple[bool, ...]
    events: tuple[core.EventClass, ...]
    preview_commit_equal: bool
    scalarized_main_action: core.PhysicalAction | None = None
    # The physical non-focal script above is what was actually executed.
    # This optional map records the branch-local Main proposal separately so
    # a candidate fork can disagree diagnostically without changing the
    # common script used for causal comparison.
    branch_main_nonfocal_actions: Mapping[int, core.PhysicalAction] | None = None


@dataclass(frozen=True)
class ShadowMainNonfocalDiagnostic:
    """Branch-local Main comparison retained without gating certification."""

    offset: int
    reference_main_nonfocal_actions: tuple[tuple[int, core.PhysicalAction], ...]
    candidate_main_nonfocal_actions: tuple[tuple[int, core.PhysicalAction], ...]
    branch_main_nonfocal_match: bool


class C3V3ShadowBackend(Protocol):
    """Minimal canonical backend required by :func:`certify_candidate_support`.

    Implementations may wrap a real ``TrainerEnvironment``.  The backend owns
    environment mechanics and fresh branch construction; this module owns no
    RNG, action selection, or model update.
    """

    def replay_prefix(self, anchor: C3V3ShadowAnchor) -> Any:
        """Return a fresh mutable branch reconstructed from the anchor."""

    def fingerprint(self, branch: Any) -> str:
        """Return the canonical pre-outcome anchor-state SHA-256 digest."""

    def scalarized_main_decision(self, branch: Any) -> adapter.ScalarizedMainDecision:
        """Return the checkpoint-backed scalarized-Main decision at the anchor."""

    def anchor_evaluation(
        self, branch: Any, decision: adapter.ScalarizedMainDecision
    ) -> Any:
        """Evaluate the scalarized-Main anchor action through canonical physics."""

    def force_focal(
        self,
        branch: Any,
        focal_physical_id: core.PhysicalId,
        offset: int,
        *,
        reference_nonfocal_actions: Mapping[int, core.PhysicalAction] | None = None,
    ) -> ShadowStep:
        """Advance one hold offset with a common reference non-focal script."""

    def release_to_main(
        self,
        branch: Any,
        offset: int,
        *,
        reference_nonfocal_actions: Mapping[int, core.PhysicalAction] | None = None,
    ) -> ShadowStep:
        """Release the focal user while executing the reference non-focal script."""


@dataclass(frozen=True)
class ShadowIntervalReceipt:
    """Auditable complete data for one paired reference/candidate offset."""

    offset: int
    reference_focal_action: core.PhysicalId
    candidate_focal_action: core.PhysicalId
    reference_r3_total: float
    candidate_r3_total: float
    reference_system_power_w: float
    candidate_system_power_w: float
    reference_energy_j: float
    candidate_energy_j: float
    reference_useful_bits: float
    candidate_useful_bits: float
    # These are the physical identities actually sent through the canonical
    # environment for each non-focal user, after any candidate-table remap.
    reference_executed_nonfocal_actions: tuple[tuple[int, core.PhysicalAction], ...] = ()
    candidate_executed_nonfocal_actions: tuple[tuple[int, core.PhysicalAction], ...] = ()


@dataclass(frozen=True)
class C3V3ShadowReceipt:
    """Result of one candidate-support attempt.

    ``PASS`` means only that the prospective certificate passed in this
    development shadow.  It does not promote the candidate to learning or
    deployment.
    """

    schema: str
    status: str
    source_id: core.PhysicalId | None
    candidate_id: core.PhysicalId | None
    anchor_fingerprint_sha256: str | None
    replayed_fresh_branches: bool
    destination_active_without_focal: bool
    main_reference_actions: tuple[core.PhysicalAction, ...]
    intervals: tuple[ShadowIntervalReceipt, ...]
    certificate: core.CompositeCertificateDecision | None
    reasons: tuple[str, ...]
    reference_useful_bits: float | None
    candidate_useful_bits: float | None
    reference_energy_j: float | None
    candidate_energy_j: float | None
    claim_ceiling: str = CLAIM_CEILING
    main_nonfocal_diagnostics: tuple[ShadowMainNonfocalDiagnostic, ...] = ()

    @property
    def certified(self) -> bool:
        """A shadow certificate pass; never a routing/deployment decision."""

        return bool(self.status == "PASS" and self.certificate and self.certificate.passed)

    @property
    def first_failed_layer(self) -> str | None:
        return None if self.certificate is None else self.certificate.first_failed_layer

    @property
    def first_failed_offset(self) -> int | None:
        return None if self.certificate is None else self.certificate.first_failed_offset

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-compatible evidence for a later short-EP caller."""

        certificate = self.certificate
        return {
            "schema": self.schema,
            "status": self.status,
            "source_id": None if self.source_id is None else list(self.source_id),
            "candidate_id": None if self.candidate_id is None else list(self.candidate_id),
            "anchor_fingerprint_sha256": self.anchor_fingerprint_sha256,
            "replayed_fresh_branches": self.replayed_fresh_branches,
            "destination_active_without_focal": self.destination_active_without_focal,
            "main_reference_actions": [
                None if value is None else list(value) for value in self.main_reference_actions
            ],
            "intervals": [
                {
                    "offset": row.offset,
                    "reference_focal_action": list(row.reference_focal_action),
                    "candidate_focal_action": list(row.candidate_focal_action),
                    "reference_r3_total": row.reference_r3_total,
                    "candidate_r3_total": row.candidate_r3_total,
                    "reference_system_power_w": row.reference_system_power_w,
                    "candidate_system_power_w": row.candidate_system_power_w,
                    "reference_energy_j": row.reference_energy_j,
                    "candidate_energy_j": row.candidate_energy_j,
                    "reference_useful_bits": row.reference_useful_bits,
                    "candidate_useful_bits": row.candidate_useful_bits,
                    "reference_executed_nonfocal_actions": {
                        str(user): (
                            None if physical_id is None else list(physical_id)
                        )
                        for user, physical_id in row.reference_executed_nonfocal_actions
                    },
                    "candidate_executed_nonfocal_actions": {
                        str(user): (
                            None if physical_id is None else list(physical_id)
                        )
                        for user, physical_id in row.candidate_executed_nonfocal_actions
                    },
                }
                for row in self.intervals
            ],
            "certificate": None
            if certificate is None
            else {
                "passed": certificate.passed,
                "first_failed_layer": certificate.first_failed_layer,
                "first_failed_offset": certificate.first_failed_offset,
                "reasons": list(certificate.reasons),
                "layer_evidence": {
                    field: bool(getattr(certificate.layer_evidence, field))
                    for field in core._LAYER_FIELDS
                },
            },
            "reasons": list(self.reasons),
            "reference_useful_bits": self.reference_useful_bits,
            "candidate_useful_bits": self.candidate_useful_bits,
            "reference_energy_j": self.reference_energy_j,
            "candidate_energy_j": self.candidate_energy_j,
            "main_nonfocal_diagnostics": [
                {
                    "offset": diagnostic.offset,
                    "reference_main_nonfocal_actions": {
                        str(user): (
                            None if physical_id is None else list(physical_id)
                        )
                        for user, physical_id in diagnostic.reference_main_nonfocal_actions
                    },
                    "candidate_main_nonfocal_actions": {
                        str(user): (
                            None if physical_id is None else list(physical_id)
                        )
                        for user, physical_id in diagnostic.candidate_main_nonfocal_actions
                    },
                    "branch_main_nonfocal_match": diagnostic.branch_main_nonfocal_match,
                }
                for diagnostic in self.main_nonfocal_diagnostics
            ],
            "claim_ceiling": self.claim_ceiling,
        }


@dataclass(frozen=True)
class _ProjectedStep:
    raw: ShadowStep
    load: adapter.CanonicalLoadProjection
    power: adapter.CanonicalPowerProjection
    served: tuple[bool, ...]
    active_beams: frozenset[core.PhysicalId]
    active_satellites: frozenset[int]


def _failure_receipt(
    *,
    source_id: core.PhysicalId | None,
    candidate_id: core.PhysicalId | None,
    reasons: Sequence[str],
    anchor_fingerprint_sha256: str | None = None,
    replayed_fresh_branches: bool = False,
    destination_active_without_focal: bool = False,
    main_reference_actions: Sequence[core.PhysicalAction] = (),
    status: str = "FAIL_CLOSED",
    certificate: core.CompositeCertificateDecision | None = None,
    main_nonfocal_diagnostics: Sequence[ShadowMainNonfocalDiagnostic] = (),
) -> C3V3ShadowReceipt:
    return C3V3ShadowReceipt(
        schema=SHADOW_SCHEMA,
        status=status,
        source_id=source_id,
        candidate_id=candidate_id,
        anchor_fingerprint_sha256=anchor_fingerprint_sha256,
        replayed_fresh_branches=bool(replayed_fresh_branches),
        destination_active_without_focal=bool(destination_active_without_focal),
        main_reference_actions=tuple(main_reference_actions),
        intervals=(),
        certificate=certificate,
        reasons=tuple(dict.fromkeys(str(reason) for reason in reasons)) or ("unknown_failure",),
        reference_useful_bits=None,
        candidate_useful_bits=None,
        reference_energy_j=None,
        candidate_energy_j=None,
        main_nonfocal_diagnostics=tuple(main_nonfocal_diagnostics),
    )


def _check_main_decision(
    decision: object, *, expected_user_count: int
) -> adapter.ScalarizedMainDecision:
    if type(decision) is not adapter.ScalarizedMainDecision:
        raise ValueError("backend Main decision must be ScalarizedMainDecision")
    if decision.objective_weights != adapter.OBJECTIVE_WEIGHTS:
        raise ValueError("Main decision weights are not (0.5,0.3,0.2)")
    if len(decision.physical_actions or ()) != expected_user_count:
        raise ValueError("Main decision must include physical IDs for every user")
    actions = tuple(decision.physical_actions or ())
    for action in actions:
        if action is not None:
            core.validate_physical_id(action, field="Main physical action")
    return decision


def _validate_step(
    raw: object,
    *,
    expected_user_count: int,
    focal_user_id: int,
) -> ShadowStep:
    if type(raw) is not ShadowStep:
        raise ValueError("backend step must be a ShadowStep")
    if raw.focal_action is None:
        raise ValueError("backend step focal action is missing")
    focal_action = core.validate_physical_id(raw.focal_action, field="step focal action")
    if not isinstance(raw.nonfocal_actions, Mapping):
        raise ValueError("step nonfocal actions must be a mapping")
    expected_users = set(range(expected_user_count)) - {focal_user_id}
    if set(raw.nonfocal_actions) != expected_users or any(
        type(uid) is not int for uid in raw.nonfocal_actions
    ):
        raise ValueError("step nonfocal actions must cover every non-focal user exactly")
    for value in raw.nonfocal_actions.values():
        if value is not None:
            core.validate_physical_id(value, field="nonfocal physical action")
    if type(raw.reentry) is not tuple or len(raw.reentry) != expected_user_count:
        raise ValueError("step reentry flags must cover every user")
    if any(type(value) is not bool for value in raw.reentry):
        raise ValueError("step reentry flags must be exact booleans")
    if type(raw.events) is not tuple or len(raw.events) != expected_user_count:
        raise ValueError("step event row must cover every user")
    if any(type(value) is not core.EventClass for value in raw.events):
        raise ValueError("step events must be EventClass values")
    if type(raw.preview_commit_equal) is not bool:
        raise ValueError("step preview/commit flag must be an exact boolean")
    if isinstance(raw.useful_bits, bool) or not isinstance(raw.useful_bits, Real):
        raise ValueError("step useful bits must be a finite nonnegative real")
    useful_bits = float(raw.useful_bits)
    if not math.isfinite(useful_bits) or useful_bits < 0.0:
        raise ValueError("step useful bits must be a finite nonnegative real")
    main_action = raw.scalarized_main_action
    if main_action is not None:
        main_action = core.validate_physical_id(main_action, field="release Main action")
    branch_main_nonfocal_actions = raw.branch_main_nonfocal_actions
    if branch_main_nonfocal_actions is not None:
        if not isinstance(branch_main_nonfocal_actions, Mapping):
            raise ValueError("branch-local Main nonfocal actions must be a mapping")
        if set(branch_main_nonfocal_actions) != expected_users or any(
            type(uid) is not int for uid in branch_main_nonfocal_actions
        ):
            raise ValueError(
                "branch-local Main nonfocal actions must cover every non-focal user"
            )
        branch_main_nonfocal_actions = {
            int(uid): (
                None
                if value is None
                else core.validate_physical_id(value, field="branch-local Main action")
            )
            for uid, value in branch_main_nonfocal_actions.items()
        }
    return ShadowStep(
        evaluation=raw.evaluation,
        focal_action=focal_action,
        nonfocal_actions=dict(raw.nonfocal_actions),
        useful_bits=useful_bits,
        reentry=raw.reentry,
        events=raw.events,
        preview_commit_equal=raw.preview_commit_equal,
        scalarized_main_action=main_action,
        branch_main_nonfocal_actions=branch_main_nonfocal_actions,
    )


def _project_step(
    raw: object, *, expected_user_count: int, focal_user_id: int
) -> _ProjectedStep:
    step = _validate_step(
        raw, expected_user_count=expected_user_count, focal_user_id=focal_user_id
    )
    load = adapter.canonical_load_projection(step.evaluation)
    power = adapter.canonical_power_projection(step.evaluation)
    snapshot = load.snapshot
    if len(snapshot.served_associations) != expected_user_count:
        raise ValueError("canonical load projection user count drifted")
    if snapshot.served_associations[focal_user_id] != step.focal_action:
        raise ValueError("canonical focal association does not match backend receipt")
    served = tuple(action is not None for action in snapshot.served_associations)
    active_beams = frozenset(snapshot.reported_active_beams)
    active_satellites = frozenset(physical_id[0] for physical_id in active_beams)
    return _ProjectedStep(step, load, power, served, active_beams, active_satellites)


def _beam_max(terms: core.PowerIntervalTerms, beam_id: core.PhysicalId) -> float:
    matches = [beam for beam in terms.beams if beam.beam_id == beam_id]
    if len(matches) != 1:
        raise ValueError(f"canonical power terms do not contain exactly one {beam_id}")
    return float(matches[0].reported_beam_max_w)


def _nonfocal_rows(
    steps: Sequence[_ProjectedStep], *, expected_user_count: int, focal_user_id: int
) -> tuple[tuple[core.PhysicalAction, ...], ...]:
    """Convert per-user maps to the pure core's stable tuple rows."""

    users = tuple(user for user in range(expected_user_count) if user != focal_user_id)
    return tuple(
        tuple(step.raw.nonfocal_actions[user] for user in users) for step in steps
    )


def _nonfocal_action_items(
    actions: Mapping[int, core.PhysicalAction], *, expected_user_count: int,
    focal_user_id: int,
) -> tuple[tuple[int, core.PhysicalAction], ...]:
    """Normalize a validated non-focal action map for diagnostic receipts."""

    expected_users = set(range(expected_user_count)) - {focal_user_id}
    if not isinstance(actions, Mapping) or set(actions) != expected_users:
        raise ValueError("diagnostic nonfocal actions must cover every non-focal user")
    return tuple(
        (user, actions[user])
        for user in sorted(expected_users)
    )


def _main_nonfocal_actions(
    step: _ProjectedStep, *, expected_user_count: int, focal_user_id: int
) -> tuple[tuple[int, core.PhysicalAction], ...]:
    """Return branch-local Main proposals, falling back for old backends."""

    proposed = step.raw.branch_main_nonfocal_actions
    if proposed is None:
        proposed = step.raw.nonfocal_actions
    return _nonfocal_action_items(
        proposed,
        expected_user_count=expected_user_count,
        focal_user_id=focal_user_id,
    )


def _main_nonfocal_diagnostic(
    offset: int,
    reference: _ProjectedStep,
    candidate: _ProjectedStep,
    *,
    expected_user_count: int,
    focal_user_id: int,
) -> ShadowMainNonfocalDiagnostic:
    reference_actions = _main_nonfocal_actions(
        reference,
        expected_user_count=expected_user_count,
        focal_user_id=focal_user_id,
    )
    candidate_actions = _main_nonfocal_actions(
        candidate,
        expected_user_count=expected_user_count,
        focal_user_id=focal_user_id,
    )
    return ShadowMainNonfocalDiagnostic(
        offset=offset,
        reference_main_nonfocal_actions=reference_actions,
        candidate_main_nonfocal_actions=candidate_actions,
        branch_main_nonfocal_match=reference_actions == candidate_actions,
    )


def _interval_receipt(
    offset: int, reference: _ProjectedStep, candidate: _ProjectedStep
) -> ShadowIntervalReceipt:
    return ShadowIntervalReceipt(
        offset=offset,
        reference_focal_action=reference.raw.focal_action,  # type: ignore[arg-type]
        candidate_focal_action=candidate.raw.focal_action,  # type: ignore[arg-type]
        reference_r3_total=reference.load.identity.canonical_r3_total,
        candidate_r3_total=candidate.load.identity.canonical_r3_total,
        reference_system_power_w=reference.power.identity.reconstructed_system_power_w,
        candidate_system_power_w=candidate.power.identity.reconstructed_system_power_w,
        reference_energy_j=(
            reference.power.identity.reconstructed_system_power_w * core.DECISION_INTERVAL_S
        ),
        candidate_energy_j=(
            candidate.power.identity.reconstructed_system_power_w * core.DECISION_INTERVAL_S
        ),
        reference_useful_bits=reference.raw.useful_bits,
        candidate_useful_bits=candidate.raw.useful_bits,
        reference_executed_nonfocal_actions=tuple(
            sorted(reference.raw.nonfocal_actions.items())
        ),
        candidate_executed_nonfocal_actions=tuple(
            sorted(candidate.raw.nonfocal_actions.items())
        ),
    )


def _full_receipt(
    *,
    source_id: core.PhysicalId,
    candidate_id: core.PhysicalId,
    anchor_fingerprint_sha256: str,
    destination_active_without_focal: bool,
    main_reference_actions: Sequence[core.PhysicalAction],
    reference: Sequence[_ProjectedStep],
    candidate: Sequence[_ProjectedStep],
    certificate: core.CompositeCertificateDecision,
    main_nonfocal_diagnostics: Sequence[ShadowMainNonfocalDiagnostic] = (),
) -> C3V3ShadowReceipt:
    intervals = tuple(
        _interval_receipt(offset, ref, cand)
        for offset, (ref, cand) in enumerate(zip(reference, candidate, strict=True))
    )
    ref_energy = sum(row.reference_energy_j for row in intervals)
    cand_energy = sum(row.candidate_energy_j for row in intervals)
    ref_bits = sum(row.reference_useful_bits for row in intervals)
    cand_bits = sum(row.candidate_useful_bits for row in intervals)
    return C3V3ShadowReceipt(
        schema=SHADOW_SCHEMA,
        status="PASS" if certificate.passed else "REJECT",
        source_id=source_id,
        candidate_id=candidate_id,
        anchor_fingerprint_sha256=anchor_fingerprint_sha256,
        replayed_fresh_branches=True,
        destination_active_without_focal=destination_active_without_focal,
        main_reference_actions=tuple(main_reference_actions),
        intervals=intervals,
        certificate=certificate,
        reasons=certificate.reasons,
        reference_useful_bits=ref_bits,
        candidate_useful_bits=cand_bits,
        reference_energy_j=ref_energy,
        candidate_energy_j=cand_energy,
        main_nonfocal_diagnostics=tuple(main_nonfocal_diagnostics),
    )


def certify_candidate_support(
    backend: C3V3ShadowBackend,
    *,
    anchor: C3V3ShadowAnchor,
    candidate_id: core.PhysicalId,
    expected_user_count: int = 100,
    scheduled_anchor: bool = True,
) -> C3V3ShadowReceipt:
    """Certify one C3 V3 candidate on fresh reference/candidate deep twins.

    The function is intentionally candidate-local: it never ranks candidates,
    chooses an outcome, updates a learner, writes a replay buffer, or routes a
    transition.  A semantic layer failure is ``REJECT`` with the composed
    first-failure receipt.  Any malformed authority/evidence/backend seam is
    ``FAIL_CLOSED`` and carries no certificate.
    """

    source: core.PhysicalId | None = None
    destination: core.PhysicalId | None = None
    main_nonfocal_diagnostics: list[ShadowMainNonfocalDiagnostic] = []
    try:
        if type(expected_user_count) is not int or expected_user_count < 1:
            raise ValueError("expected user count must be a positive exact integer")
        if type(scheduled_anchor) is not bool:
            raise ValueError("scheduled_anchor must be an exact boolean")
        checked_anchor = _validate_anchor(anchor, expected_user_count=expected_user_count)
        source = core.validate_physical_id(
            checked_anchor.source_id, field="anchor source physical ID"
        )
        destination = core.validate_physical_id(
            candidate_id, field="candidate physical ID"
        )
        if source == destination:
            raise ValueError("candidate physical ID must differ from source")
        if source[0] != destination[0]:
            raise ValueError("candidate physical ID must be on the source satellite")
        for name in (
            "replay_prefix",
            "fingerprint",
            "scalarized_main_decision",
            "anchor_evaluation",
            "force_focal",
            "release_to_main",
        ):
            if not callable(getattr(backend, name, None)):
                raise ValueError(f"backend is missing callable {name}")

        reference_branch = backend.replay_prefix(checked_anchor)
        candidate_branch = backend.replay_prefix(checked_anchor)
        if reference_branch is candidate_branch:
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("fresh_deep_twin_objects_not_distinct",),
            )
        reference_fingerprint = backend.fingerprint(reference_branch)
        candidate_fingerprint = backend.fingerprint(candidate_branch)
        if not _is_sha256(reference_fingerprint) or not _is_sha256(candidate_fingerprint):
            raise ValueError("backend anchor fingerprint must be lowercase SHA-256")
        if reference_fingerprint != checked_anchor.expected_anchor_fingerprint_sha256:
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("reference_anchor_fingerprint_not_bound_to_authority",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
            )
        if candidate_fingerprint != reference_fingerprint:
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("deep_twin_anchor_fingerprint_mismatch",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
            )

        reference_main = _check_main_decision(
            backend.scalarized_main_decision(reference_branch),
            expected_user_count=expected_user_count,
        )
        candidate_main = _check_main_decision(
            backend.scalarized_main_decision(candidate_branch),
            expected_user_count=expected_user_count,
        )
        focal_user = checked_anchor.focal_user_id
        reference_main_actions = tuple(reference_main.physical_actions or ())
        candidate_main_actions = tuple(candidate_main.physical_actions or ())
        if reference_main_actions[focal_user] != candidate_main_actions[focal_user]:
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("deep_twin_main_action_mismatch",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
                main_reference_actions=reference_main_actions,
                main_nonfocal_diagnostics=main_nonfocal_diagnostics,
            )
        main_actions = reference_main_actions
        anchor_reference_nonfocal = _nonfocal_action_items(
            {
                user: reference_main_actions[user]
                for user in range(expected_user_count)
                if user != focal_user
            },
            expected_user_count=expected_user_count,
            focal_user_id=focal_user,
        )
        anchor_candidate_nonfocal = _nonfocal_action_items(
            {
                user: candidate_main_actions[user]
                for user in range(expected_user_count)
                if user != focal_user
            },
            expected_user_count=expected_user_count,
            focal_user_id=focal_user,
        )
        if anchor_reference_nonfocal != anchor_candidate_nonfocal:
            main_nonfocal_diagnostics.append(
                ShadowMainNonfocalDiagnostic(
                    offset=-1,
                    reference_main_nonfocal_actions=anchor_reference_nonfocal,
                    candidate_main_nonfocal_actions=anchor_candidate_nonfocal,
                    branch_main_nonfocal_match=False,
                )
            )
        if main_actions[focal_user] != source:
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("Main_anchor_focal_action_is_not_source",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
                main_reference_actions=main_actions,
                main_nonfocal_diagnostics=main_nonfocal_diagnostics,
            )

        anchor_evaluation = backend.anchor_evaluation(reference_branch, reference_main)
        anchor_load = adapter.canonical_load_projection(anchor_evaluation)
        adapter.canonical_power_projection(anchor_evaluation)
        associations = anchor_load.snapshot.served_associations
        focal_user = checked_anchor.focal_user_id
        if associations[focal_user] != source:
            raise ValueError("canonical Main anchor does not serve source to focal user")
        destination_active_without_focal = any(
            associations[user] == destination for user in range(expected_user_count) if user != focal_user
        )
        qualifying_main_anchor = destination_active_without_focal
        if not qualifying_main_anchor:
            empty_certificate = None
            return _failure_receipt(
                source_id=source,
                candidate_id=destination,
                reasons=("scalarized_main_anchor_destination_not_already_active",),
                anchor_fingerprint_sha256=reference_fingerprint,
                replayed_fresh_branches=True,
                destination_active_without_focal=False,
                main_reference_actions=main_actions,
                status="REJECT",
                certificate=empty_certificate,
                main_nonfocal_diagnostics=main_nonfocal_diagnostics,
            )

        reference_steps: list[_ProjectedStep] = []
        candidate_steps: list[_ProjectedStep] = []
        for offset in range(core.HOLD_STEPS):
            reference_step = _project_step(
                backend.force_focal(reference_branch, source, offset),
                expected_user_count=expected_user_count,
                focal_user_id=focal_user,
            )
            candidate_step = _project_step(
                backend.force_focal(
                    candidate_branch,
                    destination,
                    offset,
                    reference_nonfocal_actions=dict(reference_step.raw.nonfocal_actions),
                ),
                expected_user_count=expected_user_count,
                focal_user_id=focal_user,
            )
            reference_steps.append(reference_step)
            candidate_steps.append(candidate_step)
            main_nonfocal_diagnostics.append(
                _main_nonfocal_diagnostic(
                    offset,
                    reference_step,
                    candidate_step,
                    expected_user_count=expected_user_count,
                    focal_user_id=focal_user,
                )
            )

        reference_release = _project_step(
            backend.release_to_main(reference_branch, core.FIRST_RELEASE_OFFSET),
            expected_user_count=expected_user_count,
            focal_user_id=focal_user,
        )
        candidate_release = _project_step(
            backend.release_to_main(
                candidate_branch,
                core.FIRST_RELEASE_OFFSET,
                reference_nonfocal_actions=dict(reference_release.raw.nonfocal_actions),
            ),
            expected_user_count=expected_user_count,
            focal_user_id=focal_user,
        )
        if reference_release.raw.scalarized_main_action is None:
            raise ValueError("reference release omitted scalarized Main action")
        if candidate_release.raw.scalarized_main_action is None:
            raise ValueError("candidate release omitted scalarized Main action")
        reference_steps.append(reference_release)
        candidate_steps.append(candidate_release)
        main_nonfocal_diagnostics.append(
            _main_nonfocal_diagnostic(
                core.FIRST_RELEASE_OFFSET,
                reference_release,
                candidate_release,
                expected_user_count=expected_user_count,
                focal_user_id=focal_user,
            )
        )

        forced_intervals = tuple(
            core.ForcedInterval(
                reference_physical_id=reference.raw.focal_action,
                candidate_physical_id=candidate.raw.focal_action,
                reference_recurrence_power_w=_beam_max(reference.power.terms, source),
                candidate_recurrence_power_w=_beam_max(candidate.power.terms, destination),
                canonical_link_ceiling_w=max(
                    [beam.reported_beam_max_w for beam in reference.power.terms.beams]
                    + [beam.reported_beam_max_w for beam in candidate.power.terms.beams]
                ),
                reference_served=reference.served[focal_user],
                candidate_served=candidate.served[focal_user],
            )
            for reference, candidate in zip(reference_steps[:core.HOLD_STEPS], candidate_steps[:core.HOLD_STEPS], strict=True)
        )
        grammar = core.validate_relocation_grammar(
            source_id=source,
            destination_id=destination,
            destination_already_active_without_focal=destination_active_without_focal,
            forced_intervals=forced_intervals,
            reference_release_action=reference_release.raw.focal_action,
            candidate_release_action=candidate_release.raw.focal_action,
            reference_scalarized_main_action=reference_release.raw.scalarized_main_action,
            candidate_scalarized_main_action=candidate_release.raw.scalarized_main_action,
            release_present=True,
        )
        hard_safe = core.evaluate_hard_safe_identity(
            reference_nonfocal_actions=_nonfocal_rows(
                reference_steps,
                expected_user_count=expected_user_count,
                focal_user_id=focal_user,
            ),
            candidate_nonfocal_actions=_nonfocal_rows(
                candidate_steps,
                expected_user_count=expected_user_count,
                focal_user_id=focal_user,
            ),
            reference_active_beams=tuple(step.active_beams for step in reference_steps),
            candidate_active_beams=tuple(step.active_beams for step in candidate_steps),
            reference_active_satellites=tuple(step.active_satellites for step in reference_steps),
            candidate_active_satellites=tuple(step.active_satellites for step in candidate_steps),
            preview_commit_equal=tuple(
                ref.raw.preview_commit_equal and cand.raw.preview_commit_equal
                for ref, cand in zip(reference_steps, candidate_steps, strict=True)
            ),
        )
        load_decisions = tuple(
            core.validate_relocation_load_identity(
                source_id=source,
                destination_id=destination,
                reference=reference.load.snapshot,
                candidate=candidate.load.snapshot,
            )
            for reference, candidate in zip(reference_steps[:core.HOLD_STEPS], candidate_steps[:core.HOLD_STEPS], strict=True)
        )
        power = core.evaluate_power_window(
            tuple(step.power.terms for step in reference_steps),
            tuple(step.power.terms for step in candidate_steps),
        )
        reference_useful_bits = sum(step.raw.useful_bits for step in reference_steps)
        candidate_useful_bits = sum(step.raw.useful_bits for step in candidate_steps)
        binary_proxies = core.evaluate_binary_proxies(
            reference_useful_bits=reference_useful_bits,
            candidate_useful_bits=candidate_useful_bits,
            reference_energy_j=power.reference_energy_j,
            candidate_energy_j=power.candidate_energy_j,
        )
        reference_r3 = tuple(step.load.reward_column for step in reference_steps)
        candidate_r3 = tuple(step.load.reward_column for step in candidate_steps)
        release_report = core.ReleaseReport(
            reference_focal_r3=reference_r3[core.FIRST_RELEASE_OFFSET][focal_user],
            candidate_focal_r3=candidate_r3[core.FIRST_RELEASE_OFFSET][focal_user],
            reference_system_r3=sum(reference_r3[core.FIRST_RELEASE_OFFSET]),
            candidate_system_r3=sum(candidate_r3[core.FIRST_RELEASE_OFFSET]),
        )
        through_release = core.evaluate_reward_service_events(
            reference_r3=reference_r3,
            candidate_r3=candidate_r3,
            focal_user=focal_user,
            reference_served=tuple(step.served for step in reference_steps),
            candidate_served=tuple(step.served for step in candidate_steps),
            reference_reentry=tuple(step.raw.reentry for step in reference_steps),
            candidate_reentry=tuple(step.raw.reentry for step in candidate_steps),
            reference_events=tuple(step.raw.events for step in reference_steps),
            candidate_events=tuple(step.raw.events for step in candidate_steps),
            release_report=release_report,
        )
        certificate = core.compose_candidate_certificate(
            core.CandidateCertificateParts(
                scheduled_anchor=scheduled_anchor,
                qualifying_main_anchor=qualifying_main_anchor,
                grammar=grammar,
                hard_safe=hard_safe,
                hold_loads=load_decisions,
                power=power,
                binary_proxies=binary_proxies,
                through_release=through_release,
            )
        )
        return _full_receipt(
            source_id=source,
            candidate_id=destination,
            anchor_fingerprint_sha256=reference_fingerprint,
            destination_active_without_focal=destination_active_without_focal,
            main_reference_actions=main_actions,
            reference=reference_steps,
            candidate=candidate_steps,
            certificate=certificate,
            main_nonfocal_diagnostics=main_nonfocal_diagnostics,
        )
    except (ValueError, RuntimeError, TypeError, AttributeError, IndexError) as exc:
        return _failure_receipt(
            source_id=source,
            candidate_id=destination,
            reasons=(f"{type(exc).__name__}:{exc}",),
            main_nonfocal_diagnostics=main_nonfocal_diagnostics,
        )


__all__ = [
    "SHADOW_SCHEMA",
    "CLAIM_CEILING",
    "CERTIFICATE_OFFSETS",
    "C3V3ShadowAnchor",
    "ShadowStep",
    "ShadowMainNonfocalDiagnostic",
    "C3V3ShadowBackend",
    "ShadowIntervalReceipt",
    "C3V3ShadowReceipt",
    "certify_candidate_support",
]
