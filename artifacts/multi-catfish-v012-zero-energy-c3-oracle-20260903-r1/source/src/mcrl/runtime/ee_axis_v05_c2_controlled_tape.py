"""Controlled-action-tape seam for the V0.5 C2 temporal fork.

The existing V0.4 C2 producer lets the reference and candidate branches
re-decide non-focal actions independently after the opening intervention.
That is a valid physical forecast, but it mixes the focal intervention with a
branch-local policy response.  This module provides the narrower V0.5 seam:

* a frozen Q1+Q3 reference branch produces one physical action tape;
* both branches remap that tape through their own slot tables;
* only the focal user is replaced by the C2 hold/release intervention; and
* the downstream target remains the all-user fixed-lambda EE surplus.

The module is deliberately simulator-free.  A physical runner owns branch
execution and passes immutable traces/slot tables through this interface.
No fallback action is invented when a physical key is missing or ambiguous.
Such a row is rejected closed, because branch-specific repair would violate
the controlled counterfactual.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS, SlotTable
from ..errors import MCRLContractError

# Keep this seam import-light: ``ee_axis_temporal_pairs`` imports the optional
# Torch learner stack.  These values are the sealed V0.3 temporal contract
# and are intentionally repeated here so a physical-only probe can run in an
# environment without Torch.
TEMPORAL_HORIZON_STEPS = 4
TEMPORAL_DOWNSTREAM_OFFSETS = (1, 2, 3)


CONTROLLED_TAPE_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-v1"
CONTROLLED_TAPE_PLAN_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-plan-v1"
CONTROLLED_TAPE_TARGET_SCHEMA = "multi-catfish-mcrl-v05-c2-controlled-tape-target-v1"
CONTROLLED_TAPE_FADING_MODE = "keyed-branch-independent-v1"
CONTROLLED_TAPE_OFFSETS = tuple(range(TEMPORAL_HORIZON_STEPS))
CONTROLLED_TAPE_DOWNSTREAM_OFFSETS = tuple(TEMPORAL_DOWNSTREAM_OFFSETS)
CONTROLLED_TAPE_RELEASE_REASONS = ("horizon", "support_expired")
CONTROLLED_TAPE_FOCAL_MODES = ("taped", "hold", "released")

PhysicalKey = tuple[int, int]
PhysicalAction = PhysicalKey | None


class ControlledTapeContractError(MCRLContractError):
    """A controlled C2 tape, remap, or target violates its contract."""


def _canonical_sha256(payload: object) -> str:
    try:
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise ControlledTapeContractError(
            "controlled-tape payload is not finite canonical JSON"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ControlledTapeContractError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ControlledTapeContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _finite(value: object, *, field: str, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.number)
    ):
        raise ControlledTapeContractError(f"{field} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted) or (positive and converted <= 0.0):
        qualifier = "positive finite" if positive else "finite"
        raise ControlledTapeContractError(f"{field} must be {qualifier}")
    return converted


def _physical_key(value: object, *, field: str) -> PhysicalKey:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ControlledTapeContractError(
            f"{field} must be a two-integer physical key"
        )
    return (
        _exact_int(value[0], field=f"{field}[0]"),
        _exact_int(value[1], field=f"{field}[1]"),
    )


def _physical_action(value: object, *, field: str) -> PhysicalAction:
    if value is None:
        return None
    return _physical_key(value, field=field)


def _physical_action_tuple(
    value: object, *, field: str, users: int | None = None
) -> tuple[PhysicalAction, ...]:
    if isinstance(value, (str, bytes)):
        raise ControlledTapeContractError(f"{field} must be a physical-action sequence")
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ControlledTapeContractError(
            f"{field} must be a physical-action sequence"
        ) from error
    if not values:
        raise ControlledTapeContractError(f"{field} must not be empty")
    if users is not None and len(values) != users:
        raise ControlledTapeContractError(
            f"{field} must contain exactly {users} users"
        )
    return tuple(
        _physical_action(item, field=f"{field}[{index}]")
        for index, item in enumerate(values)
    )


def _action_tuple(value: object, *, field: str, users: int) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        raise ControlledTapeContractError(f"{field} must be an action sequence")
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise ControlledTapeContractError(f"{field} must be an action sequence") from error
    if len(values) != users:
        raise ControlledTapeContractError(f"{field} user width disagrees with tape")
    actions: list[int] = []
    for index, item in enumerate(values):
        if type(item) is not int or not (-1 <= item < NUM_ACTIONS):
            raise ControlledTapeContractError(
                f"{field}[{index}] must be an action in [-1,{NUM_ACTIONS})"
            )
        actions.append(int(item))
    return tuple(actions)


def _field(value: object, name: str, *, field: str) -> Any:
    if isinstance(value, Mapping):
        if name not in value:
            raise ControlledTapeContractError(f"{field} lacks required field {name}")
        return value[name]
    if not hasattr(value, name):
        raise ControlledTapeContractError(f"{field} lacks required field {name}")
    return getattr(value, name)


def _trace_steps(reference_trace: object) -> tuple[object, ...]:
    """Normalize an object trace or a persisted trace mapping to four steps."""

    if isinstance(reference_trace, Mapping):
        fields = (
            "offsets",
            "executed_physical_actions",
            "executed_actions",
        )
        if not all(name in reference_trace for name in fields):
            raise ControlledTapeContractError(
                "reference trace mapping must contain offsets and executed actions"
            )
        offsets = tuple(reference_trace["offsets"])
        physical = tuple(reference_trace["executed_physical_actions"])
        actions = tuple(reference_trace["executed_actions"])
        if not (len(offsets) == len(physical) == len(actions)):
            raise ControlledTapeContractError(
                "reference trace mapping fields have different lengths"
            )
        return tuple(
            {
                "offset": offsets[index],
                "executed_physical_actions": physical[index],
                "executed_actions": actions[index],
            }
            for index in range(len(offsets))
        )
    if isinstance(reference_trace, (str, bytes)):
        raise ControlledTapeContractError("reference trace must be a step sequence")
    try:
        steps = tuple(reference_trace)  # type: ignore[arg-type]
    except TypeError as error:
        raise ControlledTapeContractError("reference trace must be a step sequence") from error
    return steps


def _validate_offsets(steps: Sequence[object], *, field: str) -> None:
    expected = CONTROLLED_TAPE_OFFSETS
    offsets = tuple(
        _exact_int(_field(step, "offset", field=f"{field}[{index}]"), field=f"{field}[{index}].offset")
        for index, step in enumerate(steps)
    )
    if offsets != expected:
        raise ControlledTapeContractError(
            f"{field} must contain ordered offsets {expected}, got {offsets}"
        )


def _trace_digest(steps: Sequence[object]) -> str:
    return _canonical_sha256(
        {
            "schema": "controlled-tape-reference-trace-v1",
            "steps": [
                {
                    "offset": int(_field(step, "offset", field="reference trace")),
                    "executed_actions": list(
                        _field(step, "executed_actions", field="reference trace")
                    ),
                    "executed_physical_actions": [
                        None if item is None else list(item)
                        for item in _field(
                            step,
                            "executed_physical_actions",
                            field="reference trace",
                        )
                    ],
                }
                for step in steps
            ],
        }
    )


def _tape_payload(tape: "ControlledActionTape") -> dict[str, object]:
    return {
        "schema": CONTROLLED_TAPE_SCHEMA,
        "anchor_sha256": tape.anchor_sha256,
        "reference_trace_sha256": tape.reference_trace_sha256,
        "reference_policy_sha256": tape.reference_policy_sha256,
        "common_random_field_sha256": tape.common_random_field_sha256,
        "fading_mode": tape.fading_mode,
        "focal_user": tape.focal_user,
        "steps": [
            {
                "offset": step.offset,
                "physical_actions": [
                    None if value is None else list(value)
                    for value in step.physical_actions
                ],
                "source_action_indices": list(step.source_action_indices),
            }
            for step in tape.steps
        ],
    }


@dataclass(frozen=True)
class ControlledTapeStep:
    """One immutable physical action vector from the reference branch."""

    offset: int
    physical_actions: tuple[PhysicalAction, ...]
    source_action_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "offset",
            _exact_int(self.offset, field="tape step offset"),
        )
        actions = _physical_action_tuple(
            self.physical_actions,
            field="tape step physical_actions",
        )
        source = _action_tuple(
            self.source_action_indices,
            field="tape step source_action_indices",
            users=len(actions),
        )
        object.__setattr__(self, "physical_actions", actions)
        object.__setattr__(self, "source_action_indices", source)


@dataclass(frozen=True)
class ControlledActionTape:
    """A reference-generated physical continuation tape."""

    anchor_sha256: str
    reference_trace_sha256: str
    reference_policy_sha256: str
    common_random_field_sha256: str
    fading_mode: str
    focal_user: int
    steps: tuple[ControlledTapeStep, ...]
    tape_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "anchor_sha256",
            "reference_trace_sha256",
            "reference_policy_sha256",
            "common_random_field_sha256",
        ):
            _digest(getattr(self, field), field=field)
        if self.fading_mode != CONTROLLED_TAPE_FADING_MODE:
            raise ControlledTapeContractError(
                "controlled C2 tape requires keyed branch-independent fading"
            )
        focal = _exact_int(self.focal_user, field="focal_user")
        steps = tuple(self.steps)
        if len(steps) != TEMPORAL_HORIZON_STEPS:
            raise ControlledTapeContractError(
                f"controlled C2 tape requires {TEMPORAL_HORIZON_STEPS} steps"
            )
        if any(not isinstance(step, ControlledTapeStep) for step in steps):
            raise ControlledTapeContractError("controlled C2 tape has a malformed step")
        if tuple(step.offset for step in steps) != CONTROLLED_TAPE_OFFSETS:
            raise ControlledTapeContractError("controlled C2 tape offsets are incomplete")
        users = len(steps[0].physical_actions)
        if not 0 <= focal < users:
            raise ControlledTapeContractError("focal_user lies outside the tape")
        if any(len(step.physical_actions) != users for step in steps):
            raise ControlledTapeContractError("controlled C2 tape user width changes")
        object.__setattr__(self, "focal_user", focal)
        object.__setattr__(self, "steps", steps)
        _digest(self.tape_sha256, field="tape_sha256")

    @property
    def user_count(self) -> int:
        return len(self.steps[0].physical_actions)

    def verify(self) -> str:
        actual = _canonical_sha256(_tape_payload(self))
        if actual != self.tape_sha256:
            raise ControlledTapeContractError(
                "controlled C2 tape digest disagrees with its payload"
            )
        return actual

    def as_mapping(self) -> dict[str, object]:
        self.verify()
        return {
            **_tape_payload(self),
            "tape_sha256": self.tape_sha256,
        }


def build_reference_action_tape(
    reference_trace: object,
    *,
    anchor_sha256: str,
    reference_policy_sha256: str,
    common_random_field_sha256: str,
    focal_user: int,
    reference_trace_sha256: str | None = None,
    fading_mode: str = CONTROLLED_TAPE_FADING_MODE,
) -> ControlledActionTape:
    """Build one physical tape from a frozen Q1+Q3 reference trace.

    ``reference_trace`` may be the simulator's step-object sequence or the
    persisted ``raw_trace.reference`` mapping.  The physical associations,
    rather than slot indices, are the tape authority; slot indices are kept
    only as source receipts.
    """

    steps = _trace_steps(reference_trace)
    _validate_offsets(steps, field="reference_trace")
    if fading_mode != CONTROLLED_TAPE_FADING_MODE:
        raise ControlledTapeContractError(
            "controlled C2 tape requires keyed branch-independent fading"
        )
    _digest(anchor_sha256, field="anchor_sha256")
    _digest(reference_policy_sha256, field="reference_policy_sha256")
    _digest(common_random_field_sha256, field="common_random_field_sha256")
    # Always derive the digest from the normalized trace.  A caller-supplied
    # receipt is only an assertion about that exact payload; accepting a
    # well-formed but unrelated SHA would let a persisted tape claim a
    # different reference lineage.
    actual_trace_digest = _trace_digest(steps)
    if reference_trace_sha256 is None:
        trace_digest = actual_trace_digest
    else:
        supplied_trace_digest = _digest(
            reference_trace_sha256,
            field="reference_trace_sha256",
        )
        if supplied_trace_digest != actual_trace_digest:
            raise ControlledTapeContractError(
                "reference_trace_sha256 disagrees with the actual reference trace"
            )
        trace_digest = supplied_trace_digest
    normalized: list[ControlledTapeStep] = []
    users: int | None = None
    for index, step in enumerate(steps):
        physical = _physical_action_tuple(
            _field(step, "executed_physical_actions", field=f"reference_trace[{index}]"),
            field=f"reference_trace[{index}].executed_physical_actions",
            users=users,
        )
        if users is None:
            users = len(physical)
        source_actions = _action_tuple(
            _field(step, "executed_actions", field=f"reference_trace[{index}]"),
            field=f"reference_trace[{index}].executed_actions",
            users=users,
        )
        for user, (action, physical_action) in enumerate(
            zip(source_actions, physical, strict=True)
        ):
            if (action == NO_OP_ACTION) != (physical_action is None):
                raise ControlledTapeContractError(
                    f"reference_trace[{index}] action/physical binding disagrees for user {user}"
                )
        normalized.append(
            ControlledTapeStep(
                offset=index,
                physical_actions=physical,
                source_action_indices=source_actions,
            )
        )
    assert users is not None
    focal = _exact_int(focal_user, field="focal_user")
    if focal >= users:
        raise ControlledTapeContractError("focal_user lies outside reference trace")
    if normalized[0].physical_actions[focal] is None:
        raise ControlledTapeContractError(
            "reference opening focal action must have a physical association"
        )
    tape_without_digest = ControlledActionTape(
        anchor_sha256=anchor_sha256,
        reference_trace_sha256=trace_digest,
        reference_policy_sha256=reference_policy_sha256,
        common_random_field_sha256=common_random_field_sha256,
        fading_mode=fading_mode,
        focal_user=focal,
        steps=tuple(normalized),
        tape_sha256="0" * 64,
    )
    digest = _canonical_sha256(_tape_payload(tape_without_digest))
    tape = ControlledActionTape(
        anchor_sha256=anchor_sha256,
        reference_trace_sha256=trace_digest,
        reference_policy_sha256=reference_policy_sha256,
        common_random_field_sha256=common_random_field_sha256,
        fading_mode=fading_mode,
        focal_user=focal,
        steps=tuple(normalized),
        tape_sha256=digest,
    )
    tape.verify()
    return tape


def _table_arrays(table: SlotTable, *, field: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not isinstance(table, SlotTable):
        raise ControlledTapeContractError(f"{field} must be a SlotTable")
    norads = np.asarray(table.norad_ids)
    cells = np.asarray(table.cell_ids)
    mask = np.asarray(table.mask)
    if (
        norads.shape != (NUM_ACTIONS,)
        or cells.shape != (NUM_ACTIONS,)
        or mask.shape != (NUM_ACTIONS,)
        or norads.dtype.kind not in "iu"
        or cells.dtype.kind not in "iu"
        or mask.dtype != np.bool_
    ):
        raise ControlledTapeContractError(
            f"{field} does not expose the canonical {NUM_ACTIONS}-slot table"
        )
    if np.any(mask & (norads < 0)) or np.any(mask & (cells < 0)):
        raise ControlledTapeContractError(f"{field} has a valid slot without a physical key")
    return norads, cells, mask


def _unique_action_for_physical(
    table: SlotTable,
    physical: PhysicalKey,
    *,
    field: str,
) -> int:
    norads, cells, mask = _table_arrays(table, field=field)
    matches = np.flatnonzero(
        mask & (norads == physical[0]) & (cells == physical[1])
    ).tolist()
    if len(matches) != 1:
        reason = "missing" if not matches else "duplicated"
        raise ControlledTapeContractError(
            f"{field} physical key is {reason}; matches={matches}"
        )
    return int(matches[0])


def _remap_physical_actions(
    physical_actions: Sequence[PhysicalAction],
    slot_tables: Sequence[SlotTable],
    *,
    field: str,
) -> tuple[int, ...]:
    if len(physical_actions) != len(slot_tables):
        raise ControlledTapeContractError(
            f"{field} physical actions and slot tables have different user widths"
        )
    actions: list[int] = []
    for user, (physical, table) in enumerate(zip(physical_actions, slot_tables, strict=True)):
        if physical is None:
            _table_arrays(table, field=f"{field}[{user}]")
            if table.num_valid != 0:
                raise ControlledTapeContractError(
                    f"{field}[{user}] has no-op tape data while legal actions exist"
                )
            actions.append(NO_OP_ACTION)
            continue
        actions.append(
            _unique_action_for_physical(
                table,
                physical,
                field=f"{field}[{user}]",
            )
        )
    selected = np.asarray(actions, dtype=np.int64)
    # Reuse the environment's exact no-op/mask semantics after physical remap.
    from ..env.action_contract import assert_selected_actions_valid

    try:
        checked = assert_selected_actions_valid(selected, slot_tables)
    except MCRLContractError as error:
        raise ControlledTapeContractError(str(error)) from error
    return tuple(int(value) for value in checked.tolist())


def remap_physical_actions_for_branch(
    physical_actions: Sequence[PhysicalAction],
    slot_tables: Sequence[SlotTable],
    *,
    field: str = "branch_slot_tables",
) -> tuple[int, ...]:
    """Map a reference physical vector to one branch's local action slots.

    This small public seam is used by a sequential physical runner while it
    is stepping a candidate branch.  It has the same fail-closed semantics as
    :func:`remap_controlled_tape_pair` and does not provide a fallback.
    """

    return _remap_physical_actions(
        physical_actions,
        slot_tables,
        field=field,
    )


def _nonfocal_receipt(
    *,
    offset: int,
    focal_user: int,
    reference: Sequence[PhysicalAction],
    candidate: Sequence[PhysicalAction],
) -> str:
    return _canonical_sha256(
        {
            "schema": "controlled-tape-nonfocal-equality-v1",
            "offset": offset,
            "focal_user": focal_user,
            "reference": [
                None if value is None else list(value)
                for index, value in enumerate(reference)
                if index != focal_user
            ],
            "candidate": [
                None if value is None else list(value)
                for index, value in enumerate(candidate)
                if index != focal_user
            ],
        }
    )


@dataclass(frozen=True)
class ControlledTapeStepPlan:
    """The two remapped action vectors and their physical equality receipt."""

    offset: int
    reference_actions: tuple[int, ...]
    candidate_actions: tuple[int, ...]
    reference_physical_actions: tuple[PhysicalAction, ...]
    candidate_physical_actions: tuple[PhysicalAction, ...]
    focal_mode: str
    nonfocal_equal: bool
    nonfocal_equality_sha256: str

    def __post_init__(self) -> None:
        offset = _exact_int(self.offset, field="controlled step plan offset")
        reference = _physical_action_tuple(
            self.reference_physical_actions,
            field="reference_physical_actions",
        )
        candidate = _physical_action_tuple(
            self.candidate_physical_actions,
            field="candidate_physical_actions",
            users=len(reference),
        )
        ref_actions = _action_tuple(
            self.reference_actions,
            field="reference_actions",
            users=len(reference),
        )
        cand_actions = _action_tuple(
            self.candidate_actions,
            field="candidate_actions",
            users=len(reference),
        )
        if self.focal_mode not in CONTROLLED_TAPE_FOCAL_MODES:
            raise ControlledTapeContractError("unknown controlled-tape focal mode")
        # The public dataclass cannot know the focal index; the pair verifier
        # recomputes equality with the actual focal user.
        if type(self.nonfocal_equal) is not bool:
            raise ControlledTapeContractError("nonfocal_equal must be Boolean")
        _digest(
            self.nonfocal_equality_sha256,
            field="nonfocal_equality_sha256",
        )
        object.__setattr__(self, "offset", offset)
        object.__setattr__(self, "reference_actions", ref_actions)
        object.__setattr__(self, "candidate_actions", cand_actions)
        object.__setattr__(self, "reference_physical_actions", reference)
        object.__setattr__(self, "candidate_physical_actions", candidate)


def _validate_support_release(
    support_counts: Sequence[int] | None,
    *,
    release_offset: int,
    release_reason: str,
) -> tuple[int, ...]:
    if release_reason not in CONTROLLED_TAPE_RELEASE_REASONS:
        raise ControlledTapeContractError("unknown controlled-tape release reason")
    if not 1 <= release_offset < TEMPORAL_HORIZON_STEPS:
        raise ControlledTapeContractError(
            "controlled-tape release_offset must lie in downstream offsets"
        )
    if support_counts is None:
        raise ControlledTapeContractError(
            "support_counts are required for an auditable hold/release receipt"
        )
    counts = tuple(
        _exact_int(value, field=f"support_counts[{index}]")
        for index, value in enumerate(support_counts)
    )
    if len(counts) != TEMPORAL_HORIZON_STEPS:
        raise ControlledTapeContractError("support_counts must cover offsets 0..3")
    # The hold action is physically unique at every pre-release offset.  A
    # count of two is not "more support"; it is an ambiguous physical binding
    # and must not be silently accepted.
    if any(value == 0 for value in counts[:release_offset]):
        raise ControlledTapeContractError(
            "support_counts contain an earlier zero before the first zero release"
        )
    if any(value != 1 for value in counts[:release_offset]):
        raise ControlledTapeContractError(
            "hold support_counts must be exactly one before release"
        )
    if release_reason == "support_expired":
        if counts[release_offset] != 0:
            raise ControlledTapeContractError(
                "support_expired release must occur at the first zero-support offset"
            )
        if any(value > 1 for value in counts[release_offset + 1 :]):
            raise ControlledTapeContractError(
                "post-release support_counts greater than one are ambiguous"
            )
    else:
        if release_offset != TEMPORAL_HORIZON_STEPS - 1:
            raise ControlledTapeContractError(
                "horizon release must occur at offset 3"
            )
        if any(value != 1 for value in counts):
            raise ControlledTapeContractError(
                "horizon support_counts must be exactly one at offsets 0..3"
            )
    return counts


@dataclass(frozen=True)
class ControlledTapePairPlan:
    """A reference/candidate action plan with focal-only divergence."""

    tape_sha256: str
    focal_user: int
    held_physical_key: PhysicalKey
    release_offset: int
    release_reason: str
    support_counts: tuple[int, ...] | None
    steps: tuple[ControlledTapeStepPlan, ...]
    plan_sha256: str

    def __post_init__(self) -> None:
        _digest(self.tape_sha256, field="tape_sha256")
        _physical_key(self.held_physical_key, field="held_physical_key")
        release = _exact_int(self.release_offset, field="release_offset")
        counts = _validate_support_release(
            self.support_counts,
            release_offset=release,
            release_reason=self.release_reason,
        )
        steps = tuple(self.steps)
        if len(steps) != TEMPORAL_HORIZON_STEPS:
            raise ControlledTapeContractError("controlled pair plan is incomplete")
        if any(not isinstance(step, ControlledTapeStepPlan) for step in steps):
            raise ControlledTapeContractError("controlled pair plan has a malformed step")
        if tuple(step.offset for step in steps) != CONTROLLED_TAPE_OFFSETS:
            raise ControlledTapeContractError("controlled pair plan offsets are incomplete")
        users = len(steps[0].reference_actions)
        focal = _exact_int(self.focal_user, field="focal_user")
        if not 0 <= focal < users:
            raise ControlledTapeContractError("pair-plan focal_user lies outside action vectors")
        if any(
            len(step.reference_actions) != users
            or len(step.candidate_actions) != users
            for step in steps
        ):
            raise ControlledTapeContractError("controlled pair plan user width changes")
        _digest(self.plan_sha256, field="plan_sha256")
        object.__setattr__(self, "focal_user", focal)
        object.__setattr__(self, "release_offset", release)
        object.__setattr__(self, "support_counts", counts)
        object.__setattr__(self, "steps", steps)

    def verify(self, tape: ControlledActionTape) -> str:
        tape.verify()
        if self.tape_sha256 != tape.tape_sha256:
            raise ControlledTapeContractError("pair plan is bound to a different tape")
        if self.focal_user != tape.focal_user:
            raise ControlledTapeContractError("pair plan focal user disagrees with tape")
        for index, step in enumerate(self.steps):
            tape_step = tape.steps[index]
            if step.offset != tape_step.offset:
                raise ControlledTapeContractError("pair plan offset disagrees with tape")
            expected_mode = "hold" if index < self.release_offset else "released"
            if step.focal_mode != expected_mode:
                raise ControlledTapeContractError("pair plan focal hold/release mode drifted")
            for user in range(tape.user_count):
                if step.reference_physical_actions[user] != tape_step.physical_actions[user]:
                    raise ControlledTapeContractError(
                        "reference physical action drifted from tape"
                    )
                if user == self.focal_user:
                    continue
                if step.candidate_physical_actions[user] != tape_step.physical_actions[user]:
                    raise ControlledTapeContractError(
                        "candidate nonfocal physical action is not identical to tape"
                    )
            if not step.nonfocal_equal:
                raise ControlledTapeContractError(
                    "controlled pair plan contains a nonfocal physical mismatch"
                )
            expected_receipt = _nonfocal_receipt(
                offset=index,
                focal_user=self.focal_user,
                reference=step.reference_physical_actions,
                candidate=step.candidate_physical_actions,
            )
            if step.nonfocal_equality_sha256 != expected_receipt:
                raise ControlledTapeContractError(
                    "nonfocal equality receipt disagrees with physical actions"
                )
            if index < self.release_offset:
                if step.candidate_physical_actions[self.focal_user] != self.held_physical_key:
                    raise ControlledTapeContractError(
                        "candidate focal action does not hold the declared physical key"
                    )
            elif step.candidate_physical_actions[self.focal_user] != tape_step.physical_actions[self.focal_user]:
                raise ControlledTapeContractError(
                    "candidate focal action does not follow the tape after release"
                )
        actual = _canonical_sha256(_pair_plan_payload(self))
        if actual != self.plan_sha256:
            raise ControlledTapeContractError(
                "controlled pair plan digest disagrees with its payload"
            )
        return actual

    def as_mapping(self, tape: ControlledActionTape) -> dict[str, object]:
        """Return the verified plan, including every equality receipt."""

        self.verify(tape)
        return {
            **_pair_plan_payload(self),
            "plan_sha256": self.plan_sha256,
        }


def _pair_plan_payload(plan: ControlledTapePairPlan) -> dict[str, object]:
    return {
        "schema": CONTROLLED_TAPE_PLAN_SCHEMA,
        "tape_sha256": plan.tape_sha256,
        "focal_user": plan.focal_user,
        "held_physical_key": list(plan.held_physical_key),
        "release_offset": plan.release_offset,
        "release_reason": plan.release_reason,
        "support_counts": None
        if plan.support_counts is None
        else list(plan.support_counts),
        "steps": [
            {
                "offset": step.offset,
                "reference_actions": list(step.reference_actions),
                "candidate_actions": list(step.candidate_actions),
                "reference_physical_actions": [
                    None if value is None else list(value)
                    for value in step.reference_physical_actions
                ],
                "candidate_physical_actions": [
                    None if value is None else list(value)
                    for value in step.candidate_physical_actions
                ],
                "focal_mode": step.focal_mode,
                "nonfocal_equal": step.nonfocal_equal,
                "nonfocal_equality_sha256": step.nonfocal_equality_sha256,
            }
            for step in plan.steps
        ],
    }


def remap_controlled_tape_pair(
    tape: ControlledActionTape,
    reference_slot_tables: Sequence[Sequence[SlotTable]],
    candidate_slot_tables: Sequence[Sequence[SlotTable]],
    *,
    held_physical_key: object,
    release_offset: int,
    release_reason: str,
    support_counts: Sequence[int] | None = None,
) -> ControlledTapePairPlan:
    """Remap one tape into both branches, with focal hold/release only.

    Action indices are branch-local implementation details.  The physical
    action vectors in the returned plan are the equality authority.  A
    missing or duplicated key, an illegal no-op, or any nonfocal mismatch
    raises ``ControlledTapeContractError``; there is deliberately no fallback.
    """

    if not isinstance(tape, ControlledActionTape):
        raise ControlledTapeContractError("tape must be a ControlledActionTape")
    tape.verify()
    release = _exact_int(release_offset, field="release_offset")
    counts = _validate_support_release(
        support_counts,
        release_offset=release,
        release_reason=release_reason,
    )
    held = _physical_key(held_physical_key, field="held_physical_key")
    if held == tape.steps[0].physical_actions[tape.focal_user]:
        raise ControlledTapeContractError(
            "held focal physical key must differ from the opening reference key"
        )
    reference_tables = tuple(tuple(row) for row in reference_slot_tables)
    candidate_tables = tuple(tuple(row) for row in candidate_slot_tables)
    if len(reference_tables) != TEMPORAL_HORIZON_STEPS or len(candidate_tables) != TEMPORAL_HORIZON_STEPS:
        raise ControlledTapeContractError("both branch slot-table traces must cover offsets 0..3")
    if any(len(row) != tape.user_count for row in reference_tables + candidate_tables):
        raise ControlledTapeContractError("slot-table trace user width disagrees with tape")
    plans: list[ControlledTapeStepPlan] = []
    for offset, tape_step in enumerate(tape.steps):
        ref_tables = reference_tables[offset]
        cand_tables = candidate_tables[offset]
        reference_actions = _remap_physical_actions(
            tape_step.physical_actions,
            ref_tables,
            field=f"reference_slot_tables[{offset}]",
        )
        candidate_taped_actions = _remap_physical_actions(
            tape_step.physical_actions,
            cand_tables,
            field=f"candidate_slot_tables[{offset}]",
        )
        if offset < release:
            focal_action = _unique_action_for_physical(
                cand_tables[tape.focal_user],
                held,
                field=f"candidate_slot_tables[{offset}].held_focal",
            )
            candidate_actions = list(candidate_taped_actions)
            candidate_actions[tape.focal_user] = focal_action
            candidate_physical = list(tape_step.physical_actions)
            candidate_physical[tape.focal_user] = held
            mode = "hold"
        else:
            candidate_actions = list(candidate_taped_actions)
            candidate_physical = list(tape_step.physical_actions)
            mode = "released"
        reference_physical = tuple(tape_step.physical_actions)
        candidate_physical_tuple = tuple(candidate_physical)
        if any(
            reference_physical[user] != candidate_physical_tuple[user]
            for user in range(tape.user_count)
            if user != tape.focal_user
        ):
            raise ControlledTapeContractError(
                f"nonfocal physical action mismatch at offset {offset}"
            )
        receipt = _nonfocal_receipt(
            offset=offset,
            focal_user=tape.focal_user,
            reference=reference_physical,
            candidate=candidate_physical_tuple,
        )
        plans.append(
            ControlledTapeStepPlan(
                offset=offset,
                reference_actions=reference_actions,
                candidate_actions=tuple(candidate_actions),
                reference_physical_actions=reference_physical,
                candidate_physical_actions=candidate_physical_tuple,
                focal_mode=mode,
                nonfocal_equal=True,
                nonfocal_equality_sha256=receipt,
            )
        )
    plan_without_digest = ControlledTapePairPlan(
        tape_sha256=tape.tape_sha256,
        focal_user=tape.focal_user,
        held_physical_key=held,
        release_offset=release,
        release_reason=release_reason,
        support_counts=counts,
        steps=tuple(plans),
        plan_sha256="0" * 64,
    )
    digest = _canonical_sha256(_pair_plan_payload(plan_without_digest))
    plan = ControlledTapePairPlan(
        tape_sha256=tape.tape_sha256,
        focal_user=tape.focal_user,
        held_physical_key=held,
        release_offset=release,
        release_reason=release_reason,
        support_counts=counts,
        steps=tuple(plans),
        plan_sha256=digest,
    )
    plan.verify(tape)
    return plan


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype[Any],
    shape: tuple[int, ...],
) -> np.ndarray:
    try:
        raw = np.asarray(value)
        if raw.shape != shape:
            raise ControlledTapeContractError(
                f"{field} must have shape {shape}, got {raw.shape}"
            )
        copied = np.array(raw, dtype=dtype, copy=True, order="C")
    except ControlledTapeContractError:
        raise
    except (TypeError, ValueError) as error:
        raise ControlledTapeContractError(f"{field} has an invalid numeric payload") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise ControlledTapeContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _target_payload(target: "ControlledTapeTarget") -> dict[str, object]:
    def floats(values: np.ndarray) -> list[str]:
        return [float(value).hex() for value in np.asarray(values).ravel()]

    return {
        "schema": CONTROLLED_TAPE_TARGET_SCHEMA,
        "tape_sha256": target.tape_sha256,
        "lambda_bits_per_j": float(target.lambda_bits_per_j).hex(),
        "interval_s": float(target.interval_s).hex(),
        "reference_rates_bps": floats(target.reference_rates_bps),
        "candidate_rates_bps": floats(target.candidate_rates_bps),
        "reference_system_power_w": floats(target.reference_system_power_w),
        "candidate_system_power_w": floats(target.candidate_system_power_w),
        "offset_rate_delta_bps": floats(target.offset_rate_delta_bps),
        "offset_system_energy_delta_j": floats(target.offset_system_energy_delta_j),
        "offset_surplus_bits": floats(target.offset_surplus_bits),
        "zeta2_temporal_surplus_bits": float(target.zeta2_temporal_surplus_bits).hex(),
        "mean_offset_surplus_bits": None
        if target.mean_offset_surplus_bits is None
        else float(target.mean_offset_surplus_bits).hex(),
    }


@dataclass(frozen=True)
class ControlledTapeTarget:
    """Raw and derived all-user fixed-lambda downstream target."""

    tape_sha256: str
    lambda_bits_per_j: float
    interval_s: float
    reference_rates_bps: np.ndarray
    candidate_rates_bps: np.ndarray
    reference_system_power_w: np.ndarray
    candidate_system_power_w: np.ndarray
    offset_rate_delta_bps: np.ndarray
    offset_system_energy_delta_j: np.ndarray
    offset_surplus_bits: np.ndarray
    zeta2_temporal_surplus_bits: float
    mean_offset_surplus_bits: float | None
    target_sha256: str

    def __post_init__(self) -> None:
        _digest(self.tape_sha256, field="tape_sha256")
        _finite(self.lambda_bits_per_j, field="lambda_bits_per_j", positive=True)
        _finite(self.interval_s, field="interval_s", positive=True)
        reference = np.asarray(self.reference_rates_bps)
        if reference.ndim != 2 or reference.shape[0] != TEMPORAL_HORIZON_STEPS:
            raise ControlledTapeContractError(
                "reference_rates_bps must have shape (4, users)"
            )
        users = reference.shape[1]
        candidate = _immutable_array(
            self.candidate_rates_bps,
            field="candidate_rates_bps",
            dtype=np.dtype(np.float64),
            shape=(TEMPORAL_HORIZON_STEPS, users),
        )
        reference_copy = _immutable_array(
            self.reference_rates_bps,
            field="reference_rates_bps",
            dtype=np.dtype(np.float64),
            shape=(TEMPORAL_HORIZON_STEPS, users),
        )
        if np.any(reference_copy < 0.0) or np.any(candidate < 0.0):
            raise ControlledTapeContractError("rate arrays must be nonnegative")
        ref_power = _immutable_array(
            self.reference_system_power_w,
            field="reference_system_power_w",
            dtype=np.dtype(np.float64),
            shape=(TEMPORAL_HORIZON_STEPS,),
        )
        cand_power = _immutable_array(
            self.candidate_system_power_w,
            field="candidate_system_power_w",
            dtype=np.dtype(np.float64),
            shape=(TEMPORAL_HORIZON_STEPS,),
        )
        if np.any(ref_power <= 0.0) or np.any(cand_power <= 0.0):
            raise ControlledTapeContractError("system power must be positive")
        offset_rate = _immutable_array(
            self.offset_rate_delta_bps,
            field="offset_rate_delta_bps",
            dtype=np.dtype(np.float64),
            shape=(len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS), users),
        )
        offset_energy = _immutable_array(
            self.offset_system_energy_delta_j,
            field="offset_system_energy_delta_j",
            dtype=np.dtype(np.float64),
            shape=(len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS),),
        )
        offset_surplus = _immutable_array(
            self.offset_surplus_bits,
            field="offset_surplus_bits",
            dtype=np.dtype(np.float64),
            shape=(len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS),),
        )
        total = _finite(
            self.zeta2_temporal_surplus_bits,
            field="zeta2_temporal_surplus_bits",
        )
        mean = self.mean_offset_surplus_bits
        if mean is not None:
            mean = _finite(mean, field="mean_offset_surplus_bits")
        object.__setattr__(self, "reference_rates_bps", reference_copy)
        object.__setattr__(self, "candidate_rates_bps", candidate)
        object.__setattr__(self, "reference_system_power_w", ref_power)
        object.__setattr__(self, "candidate_system_power_w", cand_power)
        object.__setattr__(self, "offset_rate_delta_bps", offset_rate)
        object.__setattr__(self, "offset_system_energy_delta_j", offset_energy)
        object.__setattr__(self, "offset_surplus_bits", offset_surplus)
        object.__setattr__(self, "zeta2_temporal_surplus_bits", total)
        object.__setattr__(self, "mean_offset_surplus_bits", mean)
        _digest(self.target_sha256, field="target_sha256")

    def verify(self) -> str:
        expected_rate = np.asarray(
            [
                self.candidate_rates_bps[offset]
                - self.reference_rates_bps[offset]
                for offset in CONTROLLED_TAPE_DOWNSTREAM_OFFSETS
            ],
            dtype=np.float64,
        )
        expected_energy = np.asarray(
            [
                self.interval_s
                * (
                    self.candidate_system_power_w[offset]
                    - self.reference_system_power_w[offset]
                )
                for offset in CONTROLLED_TAPE_DOWNSTREAM_OFFSETS
            ],
            dtype=np.float64,
        )
        expected_surplus = np.asarray(
            [
                self.interval_s * float(np.sum(expected_rate[index]))
                - self.lambda_bits_per_j * expected_energy[index]
                for index in range(len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS))
            ],
            dtype=np.float64,
        )
        if not np.array_equal(self.offset_rate_delta_bps, expected_rate):
            raise ControlledTapeContractError(
                "offset all-user rate difference disagrees with raw traces"
            )
        if not np.array_equal(self.offset_system_energy_delta_j, expected_energy):
            raise ControlledTapeContractError(
                "offset system-energy difference disagrees with raw traces"
            )
        if not np.array_equal(self.offset_surplus_bits, expected_surplus):
            raise ControlledTapeContractError(
                "offset surplus disagrees with raw traces"
            )
        expected_total = math.fsum(float(value) for value in expected_surplus)
        if not math.isclose(
            self.zeta2_temporal_surplus_bits,
            expected_total,
            rel_tol=0.0,
            abs_tol=max(1e-9, 512.0 * np.finfo(np.float64).eps * max(1.0, abs(expected_total))),
        ):
            raise ControlledTapeContractError(
                "raw controlled-tape surplus sum disagrees with offsets"
            )
        if self.mean_offset_surplus_bits is not None and not math.isclose(
            self.mean_offset_surplus_bits,
            expected_total / len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS),
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ControlledTapeContractError(
                "controlled-tape mean surplus disagrees with raw sum"
            )
        actual = _canonical_sha256(_target_payload(self))
        if actual != self.target_sha256:
            raise ControlledTapeContractError(
                "controlled-tape target digest disagrees with its payload"
            )
        return actual

    def as_mapping(self) -> dict[str, object]:
        """Return raw offset deltas and all derived target fields."""

        self.verify()
        return {
            **_target_payload(self),
            "target_sha256": self.target_sha256,
        }


def build_controlled_tape_target(
    *,
    tape_sha256: str,
    reference_rates_bps: object,
    candidate_rates_bps: object,
    reference_system_power_w: object,
    candidate_system_power_w: object,
    lambda_bits_per_j: float,
    interval_s: float,
    include_mean: bool = True,
) -> ControlledTapeTarget:
    """Materialize the all-user fixed-lambda target from paired raw traces."""

    _digest(tape_sha256, field="tape_sha256")
    reference_raw = np.asarray(reference_rates_bps)
    if reference_raw.ndim != 2 or reference_raw.shape[0] != TEMPORAL_HORIZON_STEPS:
        raise ControlledTapeContractError("reference_rates_bps must have shape (4, users)")
    users = reference_raw.shape[1]
    reference = _immutable_array(
        reference_rates_bps,
        field="reference_rates_bps",
        dtype=np.dtype(np.float64),
        shape=(TEMPORAL_HORIZON_STEPS, users),
    )
    candidate = _immutable_array(
        candidate_rates_bps,
        field="candidate_rates_bps",
        dtype=np.dtype(np.float64),
        shape=(TEMPORAL_HORIZON_STEPS, users),
    )
    ref_power = _immutable_array(
        reference_system_power_w,
        field="reference_system_power_w",
        dtype=np.dtype(np.float64),
        shape=(TEMPORAL_HORIZON_STEPS,),
    )
    cand_power = _immutable_array(
        candidate_system_power_w,
        field="candidate_system_power_w",
        dtype=np.dtype(np.float64),
        shape=(TEMPORAL_HORIZON_STEPS,),
    )
    multiplier = _finite(lambda_bits_per_j, field="lambda_bits_per_j", positive=True)
    interval = _finite(interval_s, field="interval_s", positive=True)
    delta_rate = np.asarray(
        [candidate[offset] - reference[offset] for offset in CONTROLLED_TAPE_DOWNSTREAM_OFFSETS],
        dtype=np.float64,
    )
    delta_energy = np.asarray(
        [interval * (cand_power[offset] - ref_power[offset]) for offset in CONTROLLED_TAPE_DOWNSTREAM_OFFSETS],
        dtype=np.float64,
    )
    surplus = np.asarray(
        [
            interval * float(np.sum(delta_rate[index]))
            - multiplier * delta_energy[index]
            for index in range(len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS))
        ],
        dtype=np.float64,
    )
    total = float(math.fsum(float(value) for value in surplus))
    mean = total / len(CONTROLLED_TAPE_DOWNSTREAM_OFFSETS) if include_mean else None
    provisional = ControlledTapeTarget(
        tape_sha256=tape_sha256,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        reference_rates_bps=reference,
        candidate_rates_bps=candidate,
        reference_system_power_w=ref_power,
        candidate_system_power_w=cand_power,
        offset_rate_delta_bps=delta_rate,
        offset_system_energy_delta_j=delta_energy,
        offset_surplus_bits=surplus,
        zeta2_temporal_surplus_bits=total,
        mean_offset_surplus_bits=mean,
        target_sha256="0" * 64,
    )
    digest = _canonical_sha256(_target_payload(provisional))
    target = ControlledTapeTarget(
        tape_sha256=tape_sha256,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        reference_rates_bps=reference,
        candidate_rates_bps=candidate,
        reference_system_power_w=ref_power,
        candidate_system_power_w=cand_power,
        offset_rate_delta_bps=delta_rate,
        offset_system_energy_delta_j=delta_energy,
        offset_surplus_bits=surplus,
        zeta2_temporal_surplus_bits=total,
        mean_offset_surplus_bits=mean,
        target_sha256=digest,
    )
    target.verify()
    return target


__all__ = [
    "CONTROLLED_TAPE_DOWNSTREAM_OFFSETS",
    "CONTROLLED_TAPE_FADING_MODE",
    "CONTROLLED_TAPE_FOCAL_MODES",
    "CONTROLLED_TAPE_OFFSETS",
    "CONTROLLED_TAPE_PLAN_SCHEMA",
    "CONTROLLED_TAPE_RELEASE_REASONS",
    "CONTROLLED_TAPE_SCHEMA",
    "CONTROLLED_TAPE_TARGET_SCHEMA",
    "ControlledActionTape",
    "ControlledTapeContractError",
    "ControlledTapePairPlan",
    "ControlledTapeStep",
    "ControlledTapeStepPlan",
    "ControlledTapeTarget",
    "PhysicalAction",
    "PhysicalKey",
    "build_controlled_tape_target",
    "build_reference_action_tape",
    "remap_physical_actions_for_branch",
    "remap_controlled_tape_pair",
]
