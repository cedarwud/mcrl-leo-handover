"""Diagnostic bridge from the existing C2 V3 Stage-0 receipt to V0.3A.

This adapter is for compatibility measurement only.  It accepts only rows
already certified by the older, stricter four-offset Stage-0 core and
re-expresses their preserved metrics through the new temporal-fork interface.
Historical rows predate candidate-local Main policy-alignment receipts, so the
bridge deliberately marks that gate false and can never make them eligible for
V0.3A learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import c2_temporal_fork_core as core


@dataclass(frozen=True)
class Stage0Adaptation:
    evidence: core.TemporalForkEvidence
    certificate: core.TemporalForkCertificate
    legacy_certified: bool


@dataclass(frozen=True)
class LegacyReplayLineage:
    """Hashes that only a lossless replay of the old forecast can supply."""

    opening_state_sha256: str
    opening_mask_sha256: str
    reference_branch_trace_sha256: str
    candidate_branch_trace_sha256: str


def _required(receipt: Any, field: str) -> Any:
    if not hasattr(receipt, field):
        raise core.C2ContractError(f"legacy Stage-0 receipt lacks {field}")
    return getattr(receipt, field)


def adapt_certified_stage0_receipt(
    receipt: Any,
    *,
    authority: core.ForecastAuthority,
    user_count: int,
    reference_action: int,
    candidate_action: int,
    opening_action_bindings: Sequence[core.ActionBinding],
    replay_lineage: LegacyReplayLineage,
) -> Stage0Adaptation:
    """Map one full in-memory Stage-0 receipt into the V0.3 safe-fork core.

    The historical JSON summary omitted bits and energy, so callers must pass
    the in-memory ``CandidateReceipt`` returned by
    ``c2_activation_churn_dev_support`` or a lossless equivalent.
    """

    if not isinstance(replay_lineage, LegacyReplayLineage):
        raise core.C2ContractError(
            "historical compatibility requires lossless replay lineage"
        )
    legacy_certified = _required(receipt, "certified")
    if type(legacy_certified) is not bool:
        raise core.C2ContractError("legacy certified flag must be Boolean")
    reasons = _required(receipt, "reasons")
    if isinstance(reasons, (str, bytes)) or any(
        not isinstance(value, str) for value in reasons
    ):
        raise core.C2ContractError("legacy reasons must be a string sequence")
    reason_set = frozenset(reasons)
    bindings = tuple(opening_action_bindings)
    reference_energy = _required(receipt, "reference_energy_j")
    candidate_energy = _required(receipt, "candidate_energy_j")
    beam_pulses = tuple(_required(receipt, "beam_pulses"))
    satellite_pulses = tuple(_required(receipt, "satellite_pulses"))

    # Compatibility is diagnostic only.  Cross-world physical identity in the
    # legacy receipt is not proof that non-focals followed branch-local Main.
    structural = bool(legacy_certified)
    focal_service = not bool({"focal_outage", "focal_reentry", "focal_unserved"} & reason_set)
    no_nonfocal_outage = "served_to_unserved" not in reason_set
    release = not bool(
        {"release_event_omitted", "release_event_mismatch", "release_window_incomplete"}
        & reason_set
    )
    resource_path = bool(
        beam_pulses
        or satellite_pulses
        or float(candidate_energy) < float(reference_energy)
    )
    evidence = core.TemporalForkEvidence(
        authority=authority,
        focal_user=_required(receipt, "focal_user"),
        user_count=user_count,
        reference_action=reference_action,
        candidate_action=candidate_action,
        reference_key=tuple(_required(receipt, "reference_departure_id")),
        candidate_key=tuple(_required(receipt, "candidate_id")),
        opening_action_bindings=bindings,
        opening_action_table_sha256=core.action_table_sha256(bindings),
        opening_state_sha256=replay_lineage.opening_state_sha256,
        opening_mask_sha256=replay_lineage.opening_mask_sha256,
        reference_branch_trace_sha256=replay_lineage.reference_branch_trace_sha256,
        candidate_branch_trace_sha256=replay_lineage.candidate_branch_trace_sha256,
        hold_steps=core.HOLD_STEPS,
        release_observed=release,
        branch_structurally_valid=structural,
        nonfocal_policy_aligned=False,
        focal_served_all_steps=focal_service,
        no_new_nonfocal_outage=no_nonfocal_outage,
        activation_or_energy_path=resource_path,
        reference_useful_bits=_required(receipt, "reference_useful_bits"),
        candidate_useful_bits=_required(receipt, "candidate_useful_bits"),
        reference_energy_j=reference_energy,
        candidate_energy_j=candidate_energy,
        forecast_hold_r2_margin=_required(receipt, "hold_system_r2_delta"),
        forecast_full_r2_margin=_required(receipt, "full_system_r2_delta"),
    )
    certificate = core.certify_temporal_fork(evidence)
    unexpected_failures = set(certificate.failures) - {
        core.ForkFailure.NONFOCAL_POLICY_ALIGNMENT
    }
    if legacy_certified and unexpected_failures:
        raise core.C2ContractError(
            "legacy certified receipt has failures beyond the expected V0.3A "
            "policy-alignment segregation"
        )
    return Stage0Adaptation(evidence, certificate, legacy_certified)
