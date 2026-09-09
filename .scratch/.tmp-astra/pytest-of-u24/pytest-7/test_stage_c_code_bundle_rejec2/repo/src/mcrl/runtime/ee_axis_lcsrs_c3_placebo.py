"""Fold-safe matched-support target placebo for the V0.23 LC-SRS gate."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import struct
from typing import Sequence

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_dataset import (
    LCSRS_ROW_SUPPORTED,
    LCSRSAnchorRecord,
)


LCSRS_C3_PLACEBO_SCHEMA = "multi-catfish-mcrl-v023-matched-placebo-v1"
LCSRS_C3_PLACEBO_MIN_COVERAGE = 0.80


class LCSRSC3PlaceboError(MCRLContractError):
    """A matched-placebo stratum or mapping violates the frozen contract."""


@dataclass(frozen=True, order=True)
class LCSRSPlaceboStratum:
    """The exact predecision stratum of one SUPPORTED member cell."""

    world_id: int
    phase_bin: int
    legal_opening: int
    destination_occupancy_bin: int
    committed_destination_active: int
    base_gap_bin: int

    def __post_init__(self) -> None:
        if self.phase_bin not in (0, 1, 2):
            raise LCSRSC3PlaceboError("phase_bin must represent 1-3, 4-6, or 7-9")
        if self.legal_opening != 1:
            raise LCSRSC3PlaceboError("SUPPORTED placebo rows must be legal-and-opening")
        if self.destination_occupancy_bin not in (1, 2):
            raise LCSRSC3PlaceboError("destination occupancy bin must be 1 or 2+")
        if self.committed_destination_active not in (0, 1):
            raise LCSRSC3PlaceboError("committed destination activity must be binary")
        if self.base_gap_bin not in (0, 1, 2, 3):
            raise LCSRSC3PlaceboError("base-gap bin is outside the frozen four bins")

    def key(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.world_id,
            self.phase_bin,
            self.legal_opening,
            self.destination_occupancy_bin,
            self.committed_destination_active,
            self.base_gap_bin,
        )


@dataclass(frozen=True)
class LCSRSPlaceboMapping:
    """One explicit source-target to destination-feature cyclic mapping."""

    stratum: LCSRSPlaceboStratum
    source_anchor: int
    source_user: int
    source_action: int
    destination_anchor: int
    destination_user: int
    destination_action: int
    shift: int


def _readonly(value: object, *, dtype: np.dtype) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _comparison_tolerance(left: float, right: float) -> float:
    return max(
        1.0e-12,
        1024.0 * np.finfo(np.float64).eps * max(1.0, abs(left), abs(right)),
    )


def _base_gap_bin(record: LCSRSAnchorRecord, user: int, action: int) -> int:
    reference = int(record.surface.view.reference_actions[user])
    q_reference = float(record.q12_values[user, reference])
    q_candidate = float(record.q12_values[user, action])
    gap = q_reference - q_candidate
    tolerance = _comparison_tolerance(q_reference, q_candidate)
    if abs(gap) <= tolerance:
        gap = 0.0
    if gap < 0.0:
        raise LCSRSC3PlaceboError("base gap is negative beyond the frozen tolerance")
    if gap < 0.01:
        return 0
    if gap < 0.05:
        return 1
    if gap < 0.20:
        return 2
    return 3


def placebo_stratum(
    record: LCSRSAnchorRecord,
    user: int,
    action: int,
) -> LCSRSPlaceboStratum:
    """Derive the frozen predecision stratum for one SUPPORTED cell."""

    if record.surface.row_class[user, action] != LCSRS_ROW_SUPPORTED:
        raise LCSRSC3PlaceboError("placebo strata exist only for SUPPORTED cells")
    view = record.surface.view
    opening = float(view.action_context[user, action, 3])
    if opening != 1.0 or not bool(view.action_mask[user, action]):
        raise LCSRSC3PlaceboError("SUPPORTED placebo cell is not legal-and-opening")
    users = int(view.action_context.shape[0])
    scaled_occupancy = float(view.action_context[user, action, 27]) * users
    occupancy = int(round(scaled_occupancy))
    if occupancy < 1 or not math.isclose(
        scaled_occupancy, occupancy, rel_tol=0.0, abs_tol=2.0e-6 * users
    ):
        raise LCSRSC3PlaceboError("SUPPORTED destination occupancy is malformed")
    active_raw = float(view.action_context[user, action, 12])
    if active_raw not in (0.0, 1.0):
        raise LCSRSC3PlaceboError("committed destination activity is not binary")
    return LCSRSPlaceboStratum(
        world_id=record.world_id,
        phase_bin=(record.phase - 1) // 3,
        legal_opening=1,
        destination_occupancy_bin=1 if occupancy == 1 else 2,
        committed_destination_active=int(active_raw),
        base_gap_bin=_base_gap_bin(record, user, action),
    )


def _shift(placebo_key: str, stratum: LCSRSPlaceboStratum, size: int) -> int:
    if size < 2:
        raise LCSRSC3PlaceboError("a cyclic placebo stratum needs at least two cells")
    payload = json.dumps(
        {"key": placebo_key, "stratum": stratum.key()},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (size - 1) + 1


def _placebo_digest(
    records: tuple[LCSRSAnchorRecord, ...],
    targets: tuple[np.ndarray, ...],
    mappings: tuple[LCSRSPlaceboMapping, ...],
    key_digest: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(LCSRS_C3_PLACEBO_SCHEMA.encode("ascii"))
    digest.update(key_digest.encode("ascii"))
    for record, target in zip(records, targets, strict=True):
        digest.update(record.content_digest.encode("ascii"))
        digest.update(np.ascontiguousarray(target).tobytes(order="C"))
    for mapping in mappings:
        digest.update(struct.pack(">6qI", *mapping.stratum.key(), mapping.shift))
        digest.update(
            struct.pack(
                ">6q",
                mapping.source_anchor,
                mapping.source_user,
                mapping.source_action,
                mapping.destination_anchor,
                mapping.destination_user,
                mapping.destination_action,
            )
        )
    return digest.hexdigest()


@dataclass(frozen=True)
class LCSRSMatchedPlacebo:
    """Immutable same-row-universe target permutation for one fitting fold."""

    records: tuple[LCSRSAnchorRecord, ...]
    normalized_targets_by_anchor: tuple[np.ndarray, ...]
    mappings: tuple[LCSRSPlaceboMapping, ...]
    eligible_supported_rows: int
    total_supported_rows: int
    placebo_key_sha256: str
    content_digest: str

    @property
    def coverage(self) -> float:
        return self.eligible_supported_rows / self.total_supported_rows

    @property
    def meets_coverage_gate(self) -> bool:
        return self.coverage >= LCSRS_C3_PLACEBO_MIN_COVERAGE


def build_lcsrs_matched_placebo(
    records: Sequence[LCSRSAnchorRecord],
    *,
    placebo_key: str,
) -> LCSRSMatchedPlacebo:
    """Permute only fitting-world S targets within exact frozen strata."""

    frozen_records = tuple(records)
    if not frozen_records:
        raise LCSRSC3PlaceboError("matched placebo needs at least one fitting anchor")
    if not isinstance(placebo_key, str) or not placebo_key:
        raise LCSRSC3PlaceboError("placebo_key must be a nonempty frozen string")
    identities = [(record.world_id, record.anchor_id) for record in frozen_records]
    if len(set(identities)) != len(identities):
        raise LCSRSC3PlaceboError("world/anchor identities must be unique")
    targets = [np.array(record.surface.normalized_targets, copy=True) for record in frozen_records]
    groups: dict[LCSRSPlaceboStratum, list[tuple[int, int, int]]] = {}
    for anchor_index, record in enumerate(frozen_records):
        for user, action in record.surface.cells_for_class(LCSRS_ROW_SUPPORTED).tolist():
            stratum = placebo_stratum(record, int(user), int(action))
            groups.setdefault(stratum, []).append((anchor_index, int(user), int(action)))
    total = sum(len(cells) for cells in groups.values())
    if total < 1:
        raise LCSRSC3PlaceboError("matched placebo needs a SUPPORTED row")
    mappings: list[LCSRSPlaceboMapping] = []
    eligible = 0
    for stratum in sorted(groups):
        cells = sorted(
            groups[stratum],
            key=lambda cell: (
                frozen_records[cell[0]].world_id,
                frozen_records[cell[0]].anchor_id,
                cell[1],
                cell[2],
            ),
        )
        if len(cells) < 2:
            continue
        eligible += len(cells)
        shift = _shift(placebo_key, stratum, len(cells))
        original = [
            float(frozen_records[a].surface.normalized_targets[u, action])
            for a, u, action in cells
        ]
        for destination_index, destination in enumerate(cells):
            source_index = (destination_index - shift) % len(cells)
            source = cells[source_index]
            da, du, dx = destination
            targets[da][du, dx] = np.float32(original[source_index])
            mappings.append(
                LCSRSPlaceboMapping(
                    stratum=stratum,
                    source_anchor=source[0],
                    source_user=source[1],
                    source_action=source[2],
                    destination_anchor=da,
                    destination_user=du,
                    destination_action=dx,
                    shift=shift,
                )
            )
    frozen_targets = tuple(_readonly(target, dtype=np.dtype(np.float32)) for target in targets)
    mapping_tuple = tuple(mappings)
    key_digest = hashlib.sha256(placebo_key.encode("utf-8")).hexdigest()
    digest = _placebo_digest(frozen_records, frozen_targets, mapping_tuple, key_digest)
    return LCSRSMatchedPlacebo(
        records=frozen_records,
        normalized_targets_by_anchor=frozen_targets,
        mappings=mapping_tuple,
        eligible_supported_rows=eligible,
        total_supported_rows=total,
        placebo_key_sha256=key_digest,
        content_digest=digest,
    )


__all__ = [
    "LCSRS_C3_PLACEBO_SCHEMA",
    "LCSRS_C3_PLACEBO_MIN_COVERAGE",
    "LCSRSC3PlaceboError",
    "LCSRSPlaceboStratum",
    "LCSRSPlaceboMapping",
    "LCSRSMatchedPlacebo",
    "placebo_stratum",
    "build_lcsrs_matched_placebo",
]
