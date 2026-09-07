"""Diagnostic frontier adapter for the old bounded C2 scan.

The existing scan discarded a focal user unless it had two certified
*alternative* actions.  V0.3 instead forms one binary fork from detached Main
plus each certified alternative.  Therefore one certified alternative is a
genuine two-action learning opportunity and must not be discarded.

This adapter performs no authoritative forecast, execution, or learner update.
V0.3A requires branch-local Main policy-alignment evidence that old receipts
do not contain, so historical certificates are explicitly segregated from the
online runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

import c2_stage0_receipt_adapter as bridge
import c2_temporal_fork_core as core


@dataclass(frozen=True)
class C2RuntimeFrontier:
    certificates_by_user: Mapping[int, tuple[core.TemporalForkCertificate, ...]]
    certified_candidates: int
    binary_focal_users: int
    legacy_multi_candidate_focal_users: int
    claim_ceiling: str = "C2_V0.3_LEGACY_FRONTIER_COMPATIBILITY_ONLY"


def action_bindings_from_slot_table(table: Any) -> tuple[core.ActionBinding, ...]:
    """Project one canonical focal slot table into physical action bindings."""

    for field in ("mask", "norad_ids", "cell_ids"):
        if not hasattr(table, field):
            raise core.C2ContractError(f"slot table lacks {field}")
    mask = np.asarray(table.mask)
    norads = np.asarray(table.norad_ids)
    cells = np.asarray(table.cell_ids)
    if mask.dtype != np.bool_ or mask.ndim != 1:
        raise core.C2ContractError("slot-table mask must be a one-dimensional Boolean array")
    if mask.size != core.ACTION_DIM:
        raise core.C2ContractError(
            f"slot-table mask must have exactly {core.ACTION_DIM} actions"
        )
    if norads.shape != mask.shape or cells.shape != mask.shape:
        raise core.C2ContractError("slot-table physical-ID arrays disagree with mask")
    if not np.issubdtype(norads.dtype, np.integer) or not np.issubdtype(cells.dtype, np.integer):
        raise core.C2ContractError("slot-table physical IDs must be integers")
    bindings = tuple(
        core.ActionBinding(int(action), (int(norads[action]), int(cells[action])))
        for action in np.flatnonzero(mask).tolist()
    )
    ordered = tuple(sorted(bindings, key=lambda row: row.action))
    # The digest helper also applies the core's uniqueness and ordering
    # contract, so malformed canonical tables fail at this adapter seam.
    core.action_table_sha256(ordered)
    return ordered


def _action_for_key(
    bindings: Sequence[core.ActionBinding], key: Sequence[int], *, field: str
) -> int:
    physical = tuple(key)
    matches = [row.action for row in bindings if row.physical_key == physical]
    if len(matches) != 1:
        raise core.C2ContractError(
            f"{field} physical key must map to exactly one valid action"
        )
    return int(matches[0])


def build_runtime_frontier(
    support: Any,
    *,
    authority: core.ForecastAuthority,
    slot_tables: Sequence[Any],
    user_count: int,
    replay_lineage_by_candidate: Mapping[
        tuple[int, core.PhysicalKey], bridge.LegacyReplayLineage
    ],
) -> C2RuntimeFrontier:
    """Create one binary Main/alternative certificate per old certified row."""

    if not hasattr(support, "receipts"):
        raise core.C2ContractError("forecast support lacks full candidate receipts")
    if len(slot_tables) != user_count:
        raise core.C2ContractError("slot-table count disagrees with user_count")
    preflight_seen: set[tuple[int, tuple[int, int]]] = set()
    for receipt in tuple(support.receipts):
        if not hasattr(receipt, "certified") or type(receipt.certified) is not bool:
            raise core.C2ContractError("forecast receipt certified flag is malformed")
        if not receipt.certified or tuple(receipt.candidate_id) == tuple(
            receipt.reference_departure_id
        ):
            continue
        identity = (int(receipt.focal_user), tuple(receipt.candidate_id))
        if identity in preflight_seen:
            raise core.C2ContractError(
                "forecast support repeats a certified candidate"
            )
        preflight_seen.add(identity)
    grouped: dict[int, list[core.TemporalForkCertificate]] = {}
    seen: set[tuple[int, tuple[int, int]]] = set()
    for receipt in tuple(support.receipts):
        if not hasattr(receipt, "certified") or type(receipt.certified) is not bool:
            raise core.C2ContractError("forecast receipt certified flag is malformed")
        if not receipt.certified:
            continue
        if tuple(receipt.candidate_id) == tuple(receipt.reference_departure_id):
            # A physical self-row is not a fork.  Historical scanners may
            # enumerate it, so discard it instead of aborting the full anchor.
            continue
        uid = int(receipt.focal_user)
        if not 0 <= uid < user_count:
            raise core.C2ContractError("certified focal user is outside slot tables")
        bindings = action_bindings_from_slot_table(slot_tables[uid])
        reference_action = _action_for_key(
            bindings, receipt.reference_departure_id, field="reference departure"
        )
        candidate_action = _action_for_key(
            bindings, receipt.candidate_id, field="candidate"
        )
        identity = (uid, tuple(receipt.candidate_id))
        if identity in seen:
            raise core.C2ContractError("forecast support repeats a certified candidate")
        seen.add(identity)
        replay_lineage = replay_lineage_by_candidate.get(identity)
        if not isinstance(replay_lineage, bridge.LegacyReplayLineage):
            raise core.C2ContractError(
                "certified historical candidate lacks lossless replay lineage"
            )
        adapted = bridge.adapt_certified_stage0_receipt(
            receipt,
            authority=authority,
            user_count=user_count,
            reference_action=reference_action,
            candidate_action=candidate_action,
            opening_action_bindings=bindings,
            replay_lineage=replay_lineage,
        )
        if not adapted.certificate.passed:
            raise core.C2ContractError(
                "legacy certified forecast row lacks V0.3A branch-local Main "
                "policy-alignment proof"
            )
        grouped.setdefault(uid, []).append(adapted.certificate)

    normalized = {
        uid: tuple(
            sorted(
                values,
                key=lambda value: (value.candidate_key, value.candidate_action),
            )
        )
        for uid, values in sorted(grouped.items())
    }
    legacy_multi = sum(len(values) >= 2 for values in normalized.values())
    return C2RuntimeFrontier(
        certificates_by_user=normalized,
        certified_candidates=sum(len(values) for values in normalized.values()),
        binary_focal_users=len(normalized),
        legacy_multi_candidate_focal_users=legacy_multi,
    )
