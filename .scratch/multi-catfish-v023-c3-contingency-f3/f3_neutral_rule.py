"""Declared fold-local, training-only F3 neutral-label permutation.

This C3 rule is distinct from the C1/C2 predecision source selectors.  It uses
the R2-declared strata and the imported R7 hash-shift primitive without moving
held-out labels.  The source builder imports this sole implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping, Protocol, Sequence

import numpy as np

from mcrl.runtime.ee_axis_c1_selector import C1_CLUSTER_NEUTRAL_SOURCE_RULE
from mcrl.runtime.ee_axis_c2_neutral_source import C2_NEUTRAL_SOURCE_RULE
from mcrl.runtime.ee_axis_lcsrs_c3_gate_metrics import comparison_tolerance
from mcrl.runtime.ee_axis_lcsrs_c3_placebo import (
    LCSRS_C3_PLACEBO_MIN_COVERAGE,
    _shift as r7_nonzero_cyclic_shift,
)


F3_NEUTRAL_RULE = "c3-f3-fold-local-training-only-matched-label-permutation-v1"
F3_NEUTRAL_KEY = "MCRL_V023_C3_F3_NEUTRAL_V1"
F3_NEUTRAL_KEY_SHA256 = hashlib.sha256(F3_NEUTRAL_KEY.encode("ascii")).hexdigest()
IMPORTED_NEUTRAL_RULES = {
    "c1_predecision_source_selection": C1_CLUSTER_NEUTRAL_SOURCE_RULE,
    "c2_predecision_source_selection": C2_NEUTRAL_SOURCE_RULE,
    "r7_coverage_min": LCSRS_C3_PLACEBO_MIN_COVERAGE,
    "r7_shift_implementation": "mcrl.runtime.ee_axis_lcsrs_c3_placebo._shift",
}


class F3NeutralError(ValueError):
    """A fold-safe equal-budget F3 neutral mapping is malformed."""


class NeutralRecord(Protocol):
    world: int
    lineage: int
    step: int
    view: object
    q12: np.ndarray
    targets_normalized: np.ndarray


@dataclass(frozen=True, order=True)
class F3NeutralStratum:
    world: int
    lineage: int
    phase_bin: int
    opening: int
    destination_occupancy_bin: int
    committed_destination_active: int
    base_gap_bin: int

    def __post_init__(self) -> None:
        if self.phase_bin not in (0, 1, 2):
            raise F3NeutralError("phase bin must represent steps 1-3, 4-6, or 7-9")
        if self.opening not in (0, 1):
            raise F3NeutralError("opening bin must be binary")
        if self.destination_occupancy_bin not in (0, 1, 2):
            raise F3NeutralError("occupancy bin must be 0, 1, or 2+")
        if self.committed_destination_active not in (0, 1):
            raise F3NeutralError("committed destination activity must be binary")
        if self.base_gap_bin not in (0, 1, 2, 3):
            raise F3NeutralError("base-gap bin is outside the R7 bins")

    def key(self) -> tuple[int, int, int, int, int, int, int]:
        return (
            self.world,
            self.lineage,
            self.phase_bin,
            self.opening,
            self.destination_occupancy_bin,
            self.committed_destination_active,
            self.base_gap_bin,
        )


@dataclass(frozen=True)
class F3NeutralMapping:
    stratum: F3NeutralStratum
    source_record: int
    source_user: int
    source_action: int
    destination_record: int
    destination_user: int
    destination_action: int
    shift: int


@dataclass(frozen=True)
class F3NeutralMaterialization:
    targets_by_record: tuple[np.ndarray, ...]
    mappings: tuple[F3NeutralMapping, ...]
    eligible_rows: int
    total_rows: int
    content_digest: str

    @property
    def coverage(self) -> float:
        return self.eligible_rows / self.total_rows

    @property
    def meets_coverage_gate(self) -> bool:
        return self.coverage >= LCSRS_C3_PLACEBO_MIN_COVERAGE


def _base_gap_bin(record: NeutralRecord, user: int, action: int) -> int:
    reference = int(record.view.reference_actions[user])
    q_reference = float(record.q12[user, reference])
    q_candidate = float(record.q12[user, action])
    gap = q_reference - q_candidate
    tolerance = comparison_tolerance(q_reference, q_candidate)
    if abs(gap) <= tolerance:
        gap = 0.0
    if gap < 0.0:
        raise F3NeutralError("candidate Q12 exceeds the authenticated reference")
    if gap < 0.01:
        return 0
    if gap < 0.05:
        return 1
    if gap < 0.20:
        return 2
    return 3


def neutral_stratum(record: NeutralRecord, user: int, action: int) -> F3NeutralStratum:
    view = record.view
    if not bool(view.action_mask[user, action]):
        raise F3NeutralError("neutral strata exist only for legal cells")
    users = int(view.action_mask.shape[0])
    opening_raw = float(view.action_context[user, action, 3])
    active_raw = float(view.action_context[user, action, 12])
    scaled_occupancy = float(view.action_context[user, action, 27]) * users
    occupancy = int(round(scaled_occupancy))
    if opening_raw not in (0.0, 1.0) or active_raw not in (0.0, 1.0):
        raise F3NeutralError("opening/activity descriptors are not binary")
    if occupancy < 0 or not math.isclose(
        scaled_occupancy, occupancy, rel_tol=0.0, abs_tol=2.0e-6 * users
    ):
        raise F3NeutralError("destination occupancy descriptor is malformed")
    return F3NeutralStratum(
        world=int(record.world),
        lineage=int(record.lineage),
        phase_bin=(int(record.step) - 1) // 3,
        opening=int(opening_raw),
        destination_occupancy_bin=min(occupancy, 2),
        committed_destination_active=int(active_raw),
        base_gap_bin=_base_gap_bin(record, user, action),
    )


def _content_digest(
    records: Sequence[NeutralRecord],
    targets: Sequence[np.ndarray],
    mappings: Sequence[F3NeutralMapping],
) -> str:
    digest = hashlib.sha256()
    digest.update(F3_NEUTRAL_RULE.encode("ascii"))
    digest.update(F3_NEUTRAL_KEY_SHA256.encode("ascii"))
    for record, target in zip(records, targets, strict=True):
        digest.update(
            json.dumps(
                [record.world, record.lineage, record.step], separators=(",", ":")
            ).encode("ascii")
        )
        digest.update(np.ascontiguousarray(target, dtype=np.float32).tobytes(order="C"))
    for mapping in mappings:
        digest.update(
            json.dumps(
                {
                    "stratum": mapping.stratum.key(),
                    "source": [mapping.source_record, mapping.source_user, mapping.source_action],
                    "destination": [
                        mapping.destination_record,
                        mapping.destination_user,
                        mapping.destination_action,
                    ],
                    "shift": mapping.shift,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
        )
    return digest.hexdigest()


def build_f3_neutral(
    records: Sequence[NeutralRecord],
    *,
    training_worlds: Sequence[int],
) -> F3NeutralMaterialization:
    """Apply R2's fold-local rule to training legal nonreference labels only."""

    frozen = tuple(records)
    allowed = frozenset(int(world) for world in training_worlds)
    if not frozen or not allowed:
        raise F3NeutralError("neutral materialization needs records and training worlds")
    selected = tuple(record for record in frozen if int(record.world) in allowed)
    if not selected or any(int(record.world) not in allowed for record in selected):
        raise F3NeutralError("neutral materialization crossed the training fold")
    targets = [
        np.array(record.targets_normalized, dtype=np.float32, copy=True, order="C")
        for record in selected
    ]
    groups: dict[F3NeutralStratum, list[tuple[int, int, int]]] = {}
    for record_index, record in enumerate(selected):
        view = record.view
        for user, action in np.argwhere(view.action_mask).tolist():
            if int(action) == int(view.reference_actions[int(user)]):
                continue
            stratum = neutral_stratum(record, int(user), int(action))
            groups.setdefault(stratum, []).append((record_index, int(user), int(action)))
    total = sum(len(cells) for cells in groups.values())
    if total < 1:
        raise F3NeutralError("neutral materialization has no legal nonreference row")
    mappings: list[F3NeutralMapping] = []
    eligible = 0
    for stratum in sorted(groups):
        cells = sorted(
            groups[stratum],
            key=lambda cell: (
                selected[cell[0]].world,
                selected[cell[0]].lineage,
                selected[cell[0]].step,
                cell[1],
                cell[2],
            ),
        )
        if len(cells) < 2:
            continue
        eligible += len(cells)
        shift = r7_nonzero_cyclic_shift(F3_NEUTRAL_KEY, stratum, len(cells))
        original = [
            float(selected[record_index].targets_normalized[user, action])
            for record_index, user, action in cells
        ]
        for destination_index, destination in enumerate(cells):
            source_index = (destination_index - shift) % len(cells)
            source = cells[source_index]
            dr, du, da = destination
            targets[dr][du, da] = np.float32(original[source_index])
            mappings.append(
                F3NeutralMapping(
                    stratum=stratum,
                    source_record=source[0],
                    source_user=source[1],
                    source_action=source[2],
                    destination_record=dr,
                    destination_user=du,
                    destination_action=da,
                    shift=shift,
                )
            )
    frozen_targets: list[np.ndarray] = []
    for record, target in zip(selected, targets, strict=True):
        reference = np.asarray(record.view.reference_actions, dtype=np.int64)
        if np.any(target[np.arange(reference.size), reference] != 0.0):
            raise F3NeutralError("neutral mapping moved a reference zero")
        if np.any(target[~record.view.action_mask] != 0.0):
            raise F3NeutralError("neutral mapping widened the native mask")
        target.setflags(write=False)
        frozen_targets.append(target)
    digest = _content_digest(selected, frozen_targets, mappings)
    return F3NeutralMaterialization(
        targets_by_record=tuple(frozen_targets),
        mappings=tuple(mappings),
        eligible_rows=eligible,
        total_rows=total,
        content_digest=digest,
    )


__all__ = [
    "F3_NEUTRAL_RULE",
    "F3_NEUTRAL_KEY",
    "F3_NEUTRAL_KEY_SHA256",
    "IMPORTED_NEUTRAL_RULES",
    "F3NeutralError",
    "F3NeutralStratum",
    "F3NeutralMapping",
    "F3NeutralMaterialization",
    "neutral_stratum",
    "build_f3_neutral",
]
