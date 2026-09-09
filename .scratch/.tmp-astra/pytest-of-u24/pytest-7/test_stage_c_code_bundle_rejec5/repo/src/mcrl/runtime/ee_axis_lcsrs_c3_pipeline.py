"""High-level LC-SRS C3 predecision-to-teacher binding for V0.23.

The lower-level modules deliberately expose separate authenticated seams:
the physical predecision capture, the pure topology, the structured C3 view,
and one exact two-user teacher receipt per closure pair.  This module is the
small production boundary that joins those seams into one fitting anchor.  It
does not evaluate a profile, choose a pair, or alter any target.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import struct

import numpy as np

from ..errors import MCRLContractError
from .ee_axis_lcsrs_c3_dataset import (
    LCSRSAnchorRecord,
    LCSRSAnchorSurface,
    LCSRSPairTargets,
    assemble_lcsrs_anchor_surface,
)
from .ee_axis_lcsrs_c3_encoder import LCSRSC3PredecisionCapture
from .ee_axis_lcsrs_c3_state import C3View
from .ee_axis_lcsrs_c3_teacher import (
    LCSRS_C3_TEACHER_SCHEMA,
    LCSRSTwoUserTeacher,
)
from .ee_axis_lcsrs_c3_topology import LCSRSC3AnchorTopologyReceipt


LCSRS_C3_BOUND_SCHEMA = "multi-catfish-mcrl-v023-lcsrs-c3-bound-anchor-v1"


class LCSRSC3PipelineError(MCRLContractError):
    """A predecision, topology, view, or teacher binding is invalid."""


def _digest_text(digest: "hashlib._Hash", value: str) -> None:
    encoded = value.encode("utf-8")
    digest.update(struct.pack(">I", len(encoded)))
    digest.update(encoded)


def _bound_digest(
    *,
    predecision_digest: str,
    topology_digest: str,
    view_digest: str,
    teacher_digests: tuple[str, ...],
    surface_digest: str,
    record_digest: str,
) -> str:
    """Derive one framed digest over every receipt in canonical order."""

    digest = hashlib.sha256()
    _digest_text(digest, LCSRS_C3_BOUND_SCHEMA)
    for label, value in (
        ("predecision", predecision_digest),
        ("topology", topology_digest),
        ("view", view_digest),
    ):
        _digest_text(digest, label)
        _digest_text(digest, value)
    _digest_text(digest, "teachers")
    digest.update(struct.pack(">I", len(teacher_digests)))
    for index, value in enumerate(teacher_digests):
        digest.update(struct.pack(">I", index))
        _digest_text(digest, value)
    for label, value in (("surface", surface_digest), ("record", record_digest)):
        _digest_text(digest, label)
        _digest_text(digest, value)
    return digest.hexdigest()


def _as_teacher_tuple(value: object) -> tuple[LCSRSTwoUserTeacher, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise LCSRSC3PipelineError("teacher receipts must be a sequence of receipts")
    try:
        receipts = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise LCSRSC3PipelineError(
            "teacher receipts must be a sequence of receipts"
        ) from error
    if any(not isinstance(receipt, LCSRSTwoUserTeacher) for receipt in receipts):
        raise LCSRSC3PipelineError(
            "teacher receipts contain a non-LCSRSTwoUserTeacher value"
        )
    return receipts


def _same_teacher_order(
    left: tuple[LCSRSTwoUserTeacher, ...],
    right: tuple[LCSRSTwoUserTeacher, ...],
) -> bool:
    """Compare receipt order without invoking ndarray-backed dataclass equality."""

    return len(left) == len(right) and all(
        candidate is expected
        for candidate, expected in zip(left, right, strict=True)
    )


def _verify_surface_and_record(
    *,
    surface: object,
    record: object,
    view: C3View,
    topology: LCSRSC3AnchorTopologyReceipt,
) -> None:
    """Re-run the lower-level constructors to detect post-bind tampering."""

    if not isinstance(surface, LCSRSAnchorSurface):
        raise LCSRSC3PipelineError("bound anchor surface has the wrong type")
    if not isinstance(record, LCSRSAnchorRecord):
        raise LCSRSC3PipelineError("bound anchor record has the wrong type")
    try:
        LCSRSAnchorSurface(
            view=surface.view,
            normalized_targets=surface.normalized_targets,
            row_class=surface.row_class,
            pairs=surface.pairs,
            content_digest=surface.content_digest,
        )
        LCSRSAnchorRecord(
            world_id=record.world_id,
            phase=record.phase,
            anchor_id=record.anchor_id,
            surface=surface,
            q12_values=record.q12_values,
            content_digest=record.content_digest,
        )
    except (MCRLContractError, TypeError, ValueError, AttributeError) as error:
        raise LCSRSC3PipelineError(
            f"bound surface/record verification failed: {error}"
        ) from error
    if surface.view is not view:
        raise LCSRSC3PipelineError("bound surface is not the predecision C3View")
    if record.surface is not surface:
        raise LCSRSC3PipelineError("bound record is not attached to the bound surface")
    if (
        record.world_id != topology.world_id
        or record.phase != topology.phase
        or record.anchor_id != topology.anchor_id
    ):
        raise LCSRSC3PipelineError("bound record identity disagrees with topology")
    expected_q12 = np.asarray(topology.capture.q12_snapshot.q12, dtype=np.float64)
    if not np.array_equal(record.q12_values, expected_q12):
        raise LCSRSC3PipelineError("bound record q12 disagrees with topology capture")


def _validate_inputs(
    predecision: object,
    teacher_receipts: object,
) -> tuple[
    LCSRSC3PredecisionCapture,
    LCSRSC3AnchorTopologyReceipt,
    C3View,
    tuple[LCSRSTwoUserTeacher, ...],
]:
    """Authenticate and canonically order the two sides of the binding."""

    if not isinstance(predecision, LCSRSC3PredecisionCapture):
        raise LCSRSC3PipelineError(
            "predecision must be an authenticated LCSRSC3PredecisionCapture"
        )
    topology = predecision.topology
    view = predecision.view
    if not isinstance(topology, LCSRSC3AnchorTopologyReceipt):
        raise LCSRSC3PipelineError("predecision topology has the wrong type")
    if not isinstance(view, C3View):
        raise LCSRSC3PipelineError("predecision view has the wrong type")

    try:
        # Keep each receipt's own verification visible at this production seam.
        predecision.verify()
        topology.capture.verify()
        topology.verify()
        view.verify()
        predecision.native_observation_provenance.verify()
    except (MCRLContractError, TypeError, ValueError, AttributeError) as error:
        raise LCSRSC3PipelineError(
            f"predecision/topology/view verification failed: {error}"
        ) from error

    phase = topology.phase
    if type(phase) is not int or not 1 <= phase <= 9:
        raise LCSRSC3PipelineError("fitting anchor phase must be an integer in [1,9]")
    if not topology.retained_for_fitting:
        raise LCSRSC3PipelineError(
            "topology is not retained_for_fitting (requires S/R/C classes)"
        )
    if not np.array_equal(topology.capture.action_mask, view.action_mask):
        raise LCSRSC3PipelineError("topology and C3View masks disagree")
    if not np.array_equal(topology.capture.reference_actions, view.reference_actions):
        raise LCSRSC3PipelineError("topology and C3View references disagree")

    receipts = _as_teacher_tuple(teacher_receipts)
    topology_pairs = tuple(topology.pairs)
    expected_ids = tuple(pair.pair_id for pair in topology_pairs)
    expected_id_set = set(expected_ids)
    if len(expected_id_set) != len(expected_ids):
        raise LCSRSC3PipelineError("topology pair identifiers are duplicated")

    seen: set[str] = set()
    teacher_by_id: dict[str, LCSRSTwoUserTeacher] = {}
    for receipt in receipts:
        pair_id = receipt.pair_id
        if not isinstance(pair_id, str) or not pair_id:
            raise LCSRSC3PipelineError("teacher pair_id must be a nonempty string")
        if pair_id in seen:
            raise LCSRSC3PipelineError(
                f"teacher pair identifier is duplicated: {pair_id}"
            )
        seen.add(pair_id)
        if receipt.schema != LCSRS_C3_TEACHER_SCHEMA:
            raise LCSRSC3PipelineError("teacher receipt schema drifted")
        try:
            receipt.verify()
        except (MCRLContractError, TypeError, ValueError, AttributeError) as error:
            raise LCSRSC3PipelineError(
                f"teacher receipt verification failed for {pair_id}: {error}"
            ) from error
        teacher_by_id[pair_id] = receipt

    missing = expected_id_set - seen
    extra = seen - expected_id_set
    if missing or extra or len(receipts) != len(expected_ids):
        raise LCSRSC3PipelineError(
            "teacher pair-id set disagrees with topology "
            f"(missing={sorted(missing)!r}, extra={sorted(extra)!r})"
        )

    ordered: list[LCSRSTwoUserTeacher] = []
    for pair in topology_pairs:
        teacher = teacher_by_id[pair.pair_id]
        expected_users = np.asarray(pair.member_users, dtype=np.int64)
        expected_actions = np.asarray(pair.designated_actions, dtype=np.int64)
        if not np.array_equal(teacher.member_users, expected_users):
            raise LCSRSC3PipelineError(
                f"teacher member users disagree with topology pair {pair.pair_id}"
            )
        if not np.array_equal(teacher.proposed_actions, expected_actions):
            raise LCSRSC3PipelineError(
                f"teacher proposed actions disagree with topology pair {pair.pair_id}"
            )
        targets = teacher.pair_targets
        if not isinstance(targets, LCSRSPairTargets):
            raise LCSRSC3PipelineError(
                f"teacher pair targets are invalid for {pair.pair_id}"
            )
        if (
            targets.pair_id != pair.pair_id
            or not np.array_equal(targets.user_ids, expected_users)
            or not np.array_equal(targets.action_ids, expected_actions)
        ):
            raise LCSRSC3PipelineError(
                f"teacher pair target identity disagrees with topology pair {pair.pair_id}"
            )
        references = np.asarray(topology.capture.reference_actions, dtype=np.int64)
        expected_profiles = np.repeat(references[None, :], 4, axis=0)
        expected_profiles[1, expected_users[0]] = expected_actions[0]
        expected_profiles[2, expected_users[1]] = expected_actions[1]
        expected_profiles[3, expected_users] = expected_actions
        native_mask = np.asarray(topology.capture.action_mask, dtype=np.bool_)
        for draw in teacher.draws:
            if not np.array_equal(draw.profile_actions, expected_profiles):
                raise LCSRSC3PipelineError(
                    f"teacher profile actions disagree with topology pair {pair.pair_id}"
                )
            if not np.all(
                native_mask[
                    np.arange(references.size)[None, :],
                    draw.profile_actions,
                ]
            ):
                raise LCSRSC3PipelineError(
                    f"teacher profile uses an illegal native action for {pair.pair_id}"
                )
        ordered.append(teacher)
    return predecision, topology, view, tuple(ordered)


@dataclass(frozen=True)
class LCSRSC3BoundAnchor:
    """Immutable fitting anchor after topology and all pair teachers bind."""

    predecision: LCSRSC3PredecisionCapture
    teachers: tuple[LCSRSTwoUserTeacher, ...]
    surface: LCSRSAnchorSurface
    record: LCSRSAnchorRecord
    content_digest: str = ""
    schema: str = LCSRS_C3_BOUND_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != LCSRS_C3_BOUND_SCHEMA:
            raise LCSRSC3PipelineError("bound anchor schema drifted")
        predecision, topology, view, ordered = _validate_inputs(
            self.predecision,
            self.teachers,
        )
        if not _same_teacher_order(tuple(self.teachers), ordered):
            raise LCSRSC3PipelineError(
                "bound teacher receipts must use canonical topology pair order"
            )
        _verify_surface_and_record(
            surface=self.surface,
            record=self.record,
            view=view,
            topology=topology,
        )
        expected = _bound_digest(
            predecision_digest=predecision.content_digest,
            topology_digest=topology.content_digest,
            view_digest=view.content_digest,
            teacher_digests=tuple(teacher.content_digest for teacher in ordered),
            surface_digest=self.surface.content_digest,
            record_digest=self.record.content_digest,
        )
        if self.content_digest not in {"", expected}:
            raise LCSRSC3PipelineError("bound anchor content digest mismatch")
        object.__setattr__(self, "teachers", ordered)
        object.__setattr__(self, "content_digest", expected)

    @property
    def topology(self) -> LCSRSC3AnchorTopologyReceipt:
        """The authenticated topology carried by the predecision capture."""

        return self.predecision.topology

    @property
    def view(self) -> C3View:
        """The authenticated structured view used by the surface."""

        return self.predecision.view

    @property
    def teacher_receipts(self) -> tuple[LCSRSTwoUserTeacher, ...]:
        """Canonical topology-ordered teacher receipts."""

        return self.teachers

    def verify(self) -> str:
        predecision, topology, view, ordered = _validate_inputs(
            self.predecision,
            self.teachers,
        )
        if not _same_teacher_order(tuple(self.teachers), ordered):
            raise LCSRSC3PipelineError(
                "bound teacher receipts must use canonical topology pair order"
            )
        _verify_surface_and_record(
            surface=self.surface,
            record=self.record,
            view=view,
            topology=topology,
        )
        expected = _bound_digest(
            predecision_digest=predecision.content_digest,
            topology_digest=topology.content_digest,
            view_digest=view.content_digest,
            teacher_digests=tuple(teacher.content_digest for teacher in ordered),
            surface_digest=self.surface.content_digest,
            record_digest=self.record.content_digest,
        )
        if self.content_digest != expected:
            raise LCSRSC3PipelineError("bound anchor content digest mismatch")
        return expected


def bind_lcsrs_c3_anchor(
    predecision: LCSRSC3PredecisionCapture,
    teacher_receipts: Sequence[LCSRSTwoUserTeacher] | None = None,
    *,
    teachers: Sequence[LCSRSTwoUserTeacher] | None = None,
) -> LCSRSC3BoundAnchor:
    """Bind one predecision capture to every topology-declared teacher pair."""

    if teacher_receipts is not None and teachers is not None:
        raise LCSRSC3PipelineError(
            "provide teacher_receipts or teachers, not both"
        )
    selected_teachers = teacher_receipts if teacher_receipts is not None else teachers
    if selected_teachers is None:
        raise LCSRSC3PipelineError("teacher receipts are required")
    captured, topology, view, ordered = _validate_inputs(predecision, selected_teachers)
    try:
        surface = assemble_lcsrs_anchor_surface(
            view,
            [teacher.pair_targets for teacher in ordered],
        )
        record = LCSRSAnchorRecord(
            world_id=topology.world_id,
            phase=topology.phase,
            anchor_id=topology.anchor_id,
            surface=surface,
            q12_values=topology.capture.q12_snapshot.q12,
        )
        digest = _bound_digest(
            predecision_digest=captured.content_digest,
            topology_digest=topology.content_digest,
            view_digest=view.content_digest,
            teacher_digests=tuple(teacher.content_digest for teacher in ordered),
            surface_digest=surface.content_digest,
            record_digest=record.content_digest,
        )
        return LCSRSC3BoundAnchor(
            predecision=captured,
            teachers=ordered,
            surface=surface,
            record=record,
            content_digest=digest,
        )
    except LCSRSC3PipelineError:
        raise
    except (MCRLContractError, TypeError, ValueError, AttributeError) as error:
        raise LCSRSC3PipelineError(f"LC-SRS anchor assembly failed: {error}") from error


# Keep the pipeline terminology available to callers that name the operation
# after this module rather than after its one-anchor output.
LCSRSC3BoundPipeline = LCSRSC3BoundAnchor


def bind_lcsrs_c3_pipeline(
    predecision: LCSRSC3PredecisionCapture,
    teacher_receipts: Sequence[LCSRSTwoUserTeacher] | None = None,
    *,
    teachers: Sequence[LCSRSTwoUserTeacher] | None = None,
) -> LCSRSC3BoundAnchor:
    """Alias for :func:`bind_lcsrs_c3_anchor` with pipeline terminology."""

    return bind_lcsrs_c3_anchor(
        predecision,
        teacher_receipts,
        teachers=teachers,
    )


__all__ = [
    "LCSRS_C3_BOUND_SCHEMA",
    "LCSRSC3PipelineError",
    "LCSRSC3BoundAnchor",
    "LCSRSC3BoundPipeline",
    "bind_lcsrs_c3_anchor",
    "bind_lcsrs_c3_pipeline",
]
