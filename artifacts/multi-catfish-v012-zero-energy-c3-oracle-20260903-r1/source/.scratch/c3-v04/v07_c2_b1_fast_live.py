"""Development-only live adapter for the V0.7 C2 B1 fast screen.

This module is deliberately a small source-construction seam.  It is not a
trainer, a policy selector, or an evidence writer.  A rapid runner supplies
two already-reset branches at the same opening anchor and a physical tape
that was produced by the frozen Q1+Q3 reference behavior.  The adapter then
replays exactly the three registered successor offsets ``k=1,2,3``:

* reference and candidate opening vectors must differ at the focal user only;
* every non-focal successor action is the same physical ``(NORAD, cell)`` key
  remapped through the branch-local slot table;
* the candidate focal user holds its opening physical key only while that key
  has one legal slot; and
* after support is lost, the caller's explicit validation carrier is passed
  to ``step_without_user`` and the removal is absorbing for the remainder.

The carrier is only a native-action envelope required by the environment's
validation boundary.  Its focal action is overwritten by the removal seam and
is never executed.  No alternate focal association, policy re-decision,
fallback, target inspection, or replacement row is introduced here.

The returned object is a development diagnostic.  Its claim ceiling is
explicitly below held-out EE evidence and below a training-ready source
receipt.  The formal runner must still bind the shared manifest, provenance,
and final B1 source contract before opening a formal gate.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS, SlotTable
from mcrl.errors import MCRLContractError
from mcrl.runtime.ee_axis_v05_c2_controlled_tape import (
    remap_physical_actions_for_branch,
)
from mcrl.runtime.ee_axis_v07_c2_parallel_targets import (
    FocalSegmentContinuationSurplus,
    focal_segment_continuation_target,
)


B1_FAST_LIVE_SCHEMA = "multi-catfish-mcrl-v07-c2-b1-fast-live-v1"
B1_FAST_LIVE_TAPE_SCHEMA = "multi-catfish-mcrl-v07-c2-b1-reference-tape-v1"
B1_SUCCESSOR_OFFSETS = (1, 2, 3)
B1_CLAIM_CEILING = (
    "development-only-source-mechanics-and-signed-target-diagnostic;"
    "not-formal-evidence;not-trained;not-heldout-ee"
)

PhysicalKey = tuple[int, int]
PhysicalAction = PhysicalKey | None
FocalRemovalCarrier = Callable[[object, object, int], int]


class B1FastLiveError(MCRLContractError):
    """A B1 fast-live source row cannot be produced without weakening its seam."""


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
        raise B1FastLiveError("B1 payload is not finite canonical JSON") from error
    return hashlib.sha256(encoded).hexdigest()


def _physical_key(value: object, *, field: str) -> PhysicalKey:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise B1FastLiveError(f"{field} must be a two-integer physical key")
    if any(type(item) is not int or item < 0 for item in value):
        raise B1FastLiveError(f"{field} must contain non-negative exact integers")
    return (int(value[0]), int(value[1]))


def _physical_action(value: object, *, field: str) -> PhysicalAction:
    if value is None:
        return None
    return _physical_key(value, field=field)


def _physical_vector(
    value: object,
    *,
    field: str,
    users: int | None = None,
) -> tuple[PhysicalAction, ...]:
    if isinstance(value, (str, bytes)):
        raise B1FastLiveError(f"{field} must be a physical-action vector")
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise B1FastLiveError(f"{field} must be a physical-action vector") from error
    if not values:
        raise B1FastLiveError(f"{field} must not be empty")
    if users is not None and len(values) != users:
        raise B1FastLiveError(f"{field} must contain exactly {users} users")
    return tuple(
        _physical_action(item, field=f"{field}[{index}]")
        for index, item in enumerate(values)
    )


def _native_vector(value: object, *, field: str, users: int) -> np.ndarray:
    try:
        values = tuple(value)  # type: ignore[arg-type]
    except TypeError as error:
        raise B1FastLiveError(f"{field} must be a native action vector") from error
    if len(values) != users:
        raise B1FastLiveError(f"{field} must contain exactly {users} users")
    if any(
        isinstance(item, (bool, np.bool_))
        or not isinstance(item, (int, np.integer))
        for item in values
    ):
        raise B1FastLiveError(f"{field} must contain exact integer actions")
    actions = np.asarray([int(item) for item in values], dtype=np.int64)
    if np.any(actions < NO_OP_ACTION) or np.any(actions >= NUM_ACTIONS):
        raise B1FastLiveError(
            f"{field} actions must be in [{NO_OP_ACTION},{NUM_ACTIONS})"
        )
    actions.setflags(write=False)
    return actions


def _table_for_user(slot_tables: Sequence[object], user: int, *, field: str) -> SlotTable:
    if user < 0 or user >= len(slot_tables):
        raise B1FastLiveError(f"{field} user index is outside slot tables")
    table = slot_tables[user]
    if not isinstance(table, SlotTable):
        raise B1FastLiveError(f"{field}[{user}] must be a SlotTable")
    return table


def _action_to_physical(
    action: int,
    table: SlotTable,
    *,
    field: str,
) -> PhysicalAction:
    if type(action) is not int or not -1 <= action < NUM_ACTIONS:
        raise B1FastLiveError(f"{field} is outside the native action space")
    if action == NO_OP_ACTION:
        if table.num_valid != 0:
            raise B1FastLiveError(
                f"{field} uses no-op while the reference mask has legal actions"
            )
        return None
    try:
        association = table.association(action)
    except (MCRLContractError, ValueError) as error:
        raise B1FastLiveError(f"{field} is not legal under its reference mask") from error
    return (int(association.norad_id), int(association.cell_id))


def precommit_q13_nonfocal_tape(
    *,
    reference_actions: Sequence[Sequence[int] | np.ndarray],
    reference_slot_tables: Sequence[Sequence[SlotTable]],
    focal_user: int,
) -> "B1PhysicalActionTape":
    """Freeze one physical Q1+Q3 reference tape for offsets 1, 2, and 3.

    The inputs are the reference branch's already-produced native behavior
    decisions and local tables.  Only physical identities are retained for
    replay.  This helper never evaluates a target or inspects an EE outcome;
    it therefore cannot turn a measured result into a replacement action.
    """

    if len(reference_actions) != len(B1_SUCCESSOR_OFFSETS):
        raise B1FastLiveError(
            "reference Q1+Q3 tape must contain exactly offsets k=1,2,3"
        )
    if len(reference_slot_tables) != len(B1_SUCCESSOR_OFFSETS):
        raise B1FastLiveError(
            "reference slot-table tape must contain exactly offsets k=1,2,3"
        )
    first_actions = tuple(reference_actions[0])
    users = len(first_actions)
    if users < 1 or type(focal_user) is not int or not 0 <= focal_user < users:
        raise B1FastLiveError("focal_user is outside the reference tape")
    vectors: list[tuple[PhysicalAction, ...]] = []
    native_receipt: list[list[int]] = []
    for offset_index, (actions_raw, tables_raw) in enumerate(
        zip(reference_actions, reference_slot_tables, strict=True),
        start=1,
    ):
        actions = _native_vector(
            actions_raw,
            field=f"reference_actions[{offset_index}]",
            users=users,
        )
        tables = tuple(tables_raw)
        if len(tables) != users:
            raise B1FastLiveError(
                f"reference_slot_tables[{offset_index}] has the wrong user width"
            )
        physical = tuple(
            _action_to_physical(
                int(action),
                _table_for_user(
                    tables,
                    user,
                    field=f"reference_slot_tables[{offset_index}]",
                ),
                field=f"reference_actions[{offset_index}][{user}]",
            )
            for user, action in enumerate(actions.tolist())
        )
        vectors.append(physical)
        native_receipt.append([int(action) for action in actions.tolist()])
    return B1PhysicalActionTape(
        physical_actions=tuple(vectors),
        source_actions=tuple(tuple(row) for row in native_receipt),
        focal_user=focal_user,
    )


@dataclass(frozen=True)
class B1PhysicalActionTape:
    """Immutable physical identities from the frozen Q1+Q3 reference branch."""

    physical_actions: tuple[tuple[PhysicalAction, ...], ...]
    focal_user: int
    source_actions: tuple[tuple[int, ...], ...] | None = None
    schema: str = B1_FAST_LIVE_TAPE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != B1_FAST_LIVE_TAPE_SCHEMA:
            raise B1FastLiveError("B1 tape schema is stale")
        if tuple(B1_SUCCESSOR_OFFSETS) != (1, 2, 3):
            raise B1FastLiveError("B1 successor offsets drifted")
        rows = tuple(
            _physical_vector(
                row,
                field=f"physical_actions[{index}]",
            )
            for index, row in enumerate(self.physical_actions)
        )
        if len(rows) != len(B1_SUCCESSOR_OFFSETS):
            raise B1FastLiveError(
                "B1 physical tape must contain exactly offsets k=1,2,3"
            )
        users = len(rows[0])
        if type(self.focal_user) is not int or not 0 <= self.focal_user < users:
            raise B1FastLiveError("B1 tape focal_user is outside its user axis")
        if any(len(row) != users for row in rows):
            raise B1FastLiveError("B1 tape user width changes across offsets")
        if self.source_actions is not None:
            source = tuple(tuple(row) for row in self.source_actions)
            if len(source) != len(rows) or any(len(row) != users for row in source):
                raise B1FastLiveError("B1 tape source-action receipt is malformed")
            if any(
                type(action) is not int or not -1 <= action < NUM_ACTIONS
                for row in source
                for action in row
            ):
                raise B1FastLiveError("B1 tape source-action receipt is malformed")
            object.__setattr__(self, "source_actions", source)
        object.__setattr__(self, "physical_actions", rows)

    @property
    def user_count(self) -> int:
        return len(self.physical_actions[0])

    @property
    def tape_sha256(self) -> str:
        return _canonical_sha256(self.as_mapping(include_digest=False))

    def as_mapping(self, *, include_digest: bool = True) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "focal_user": self.focal_user,
            "offsets": list(B1_SUCCESSOR_OFFSETS),
            "physical_actions": [
                [None if value is None else list(value) for value in row]
                for row in self.physical_actions
            ],
        }
        if self.source_actions is not None:
            body["source_actions"] = [list(row) for row in self.source_actions]
        if include_digest:
            body["tape_sha256"] = self.tape_sha256
        return body


def _normalize_tape(value: object, *, focal_user: int, users: int) -> B1PhysicalActionTape:
    if isinstance(value, B1PhysicalActionTape):
        tape = value
    else:
        try:
            rows = tuple(value)  # type: ignore[arg-type]
        except TypeError as error:
            raise B1FastLiveError("nonfocal tape is not a physical-action sequence") from error
        tape = B1PhysicalActionTape(
            physical_actions=tuple(
                _physical_vector(row, field=f"reference_tape[{index}]", users=users)
                for index, row in enumerate(rows)
            ),
            focal_user=focal_user,
        )
    if tape.focal_user != focal_user or tape.user_count != users:
        raise B1FastLiveError("reference tape user/focal binding disagrees")
    return tape


def _observation(branch: object) -> object:
    outcome = getattr(branch, "last_outcome", None)
    if outcome is not None:
        observation = getattr(outcome, "observation", None)
        if observation is not None:
            return observation
    observation = getattr(branch, "observation", None)
    if observation is not None:
        return observation
    raise B1FastLiveError("branch exposes no current StepObservation")


def _slot_tables(branch: object, *, field: str) -> tuple[SlotTable, ...]:
    observation = _observation(branch)
    candidates = getattr(observation, "candidates", None)
    tables_raw = (
        getattr(candidates, "slot_tables", None)
        if candidates is not None
        else getattr(observation, "slot_tables", None)
    )
    if tables_raw is None:
        raise B1FastLiveError(f"{field} observation exposes no slot tables")
    try:
        tables = tuple(tables_raw)
    except TypeError as error:
        raise B1FastLiveError(f"{field} slot tables are malformed") from error
    if not tables or any(not isinstance(table, SlotTable) for table in tables):
        raise B1FastLiveError(f"{field} slot tables are malformed")
    return tables


def _environment(branch: object) -> object:
    environment = getattr(branch, "environment", branch)
    if environment is None:
        raise B1FastLiveError("branch exposes no StepEnvironment")
    return environment


def _physical_match_count(table: SlotTable, key: PhysicalKey) -> int:
    return int(
        np.count_nonzero(
            np.asarray(table.mask, dtype=np.bool_)
            & (np.asarray(table.norad_ids, dtype=np.int64) == key[0])
            & (np.asarray(table.cell_ids, dtype=np.int64) == key[1])
        )
    )


def _map_one(physical: PhysicalAction, table: SlotTable, *, field: str) -> int:
    try:
        return int(
            remap_physical_actions_for_branch(
                (physical,),
                (table,),
                field=field,
            )[0]
        )
    except MCRLContractError as error:
        raise B1FastLiveError(str(error)) from error


def _remap_reference(
    physical: Sequence[PhysicalAction],
    tables: Sequence[SlotTable],
    *,
    field: str,
) -> np.ndarray:
    if len(physical) != len(tables):
        raise B1FastLiveError(f"{field} physical/tables user widths disagree")
    actions = np.asarray(
        [
            _map_one(value, table, field=f"{field}[{user}]")
            for user, (value, table) in enumerate(zip(physical, tables, strict=True))
        ],
        dtype=np.int64,
    )
    actions.setflags(write=False)
    return actions


def _remap_candidate_nonfocal(
    physical: Sequence[PhysicalAction],
    tables: Sequence[SlotTable],
    *,
    focal_user: int,
    focal_action: int,
    field: str,
) -> np.ndarray:
    if len(physical) != len(tables):
        raise B1FastLiveError(f"{field} physical/tables user widths disagree")
    actions = np.empty(len(tables), dtype=np.int64)
    for user, (value, table) in enumerate(zip(physical, tables, strict=True)):
        if user == focal_user:
            actions[user] = int(focal_action)
        else:
            actions[user] = _map_one(value, table, field=f"{field}[{user}]")
    actions.setflags(write=False)
    return actions


def _opening_check(
    reference_actions: object,
    candidate_actions: object,
    reference_physical: object,
    candidate_physical: object,
    *,
    focal_user: int,
) -> tuple[np.ndarray, np.ndarray, tuple[PhysicalAction, ...], tuple[PhysicalAction, ...]]:
    ref = _native_vector(
        reference_actions,
        field="reference_opening_actions",
        users=len(tuple(reference_actions)),  # type: ignore[arg-type]
    )
    users = len(ref)
    cand = _native_vector(
        candidate_actions,
        field="candidate_opening_actions",
        users=users,
    )
    if type(focal_user) is not int or not 0 <= focal_user < users:
        raise B1FastLiveError("opening focal_user is outside the action vector")
    differences = np.flatnonzero(ref != cand).tolist()
    if differences != [focal_user]:
        raise B1FastLiveError(
            "candidate/reference opening actions must differ at the focal user only"
        )
    ref_physical = _physical_vector(
        reference_physical,
        field="reference_opening_physical_actions",
        users=users,
    )
    cand_physical = _physical_vector(
        candidate_physical,
        field="candidate_opening_physical_actions",
        users=users,
    )
    if any(
        ref_physical[user] != cand_physical[user]
        for user in range(users)
        if user != focal_user
    ):
        raise B1FastLiveError(
            "candidate/reference opening physical actions must differ at focal only"
        )
    if ref_physical[focal_user] is None or cand_physical[focal_user] is None:
        raise B1FastLiveError("both opening focal actions must name physical keys")
    if ref_physical[focal_user] == cand_physical[focal_user]:
        raise B1FastLiveError("candidate opening focal physical key must change")
    return ref, cand, ref_physical, cand_physical


def _step(
    branch: object,
    actions: np.ndarray,
    rng: object,
    *,
    focal_user: int,
    remove_focal: bool,
    offset: int,
) -> object:
    method_name = "step_without_user" if remove_focal else "step"
    method = getattr(branch, method_name, None)
    if not callable(method):
        raise B1FastLiveError(f"branch does not expose {method_name}")
    try:
        if remove_focal:
            result = method(actions, rng, focal_user=focal_user)
        else:
            result = method(actions, rng)
    except Exception as error:
        raise B1FastLiveError(
            f"{method_name} failed at successor offset {offset}: {error}"
        ) from error
    if offset < B1_SUCCESSOR_OFFSETS[-1] and bool(getattr(result, "done", False)):
        raise B1FastLiveError(
            f"branch terminated before required B1 successor offset {offset}"
        )
    return result


def _last_outcome(branch: object, *, offset: int) -> object:
    outcome = getattr(branch, "last_outcome", None)
    if outcome is None:
        raise B1FastLiveError(f"branch has no committed outcome at offset {offset}")
    return outcome


def _raw_committed(outcome: object, *, focal_user: int, field: str) -> tuple[float, float]:
    try:
        rates = np.asarray(getattr(outcome, "link_rate_bps"), dtype=np.float64)
        power = float(getattr(outcome, "system_power_w"))
    except (TypeError, ValueError, AttributeError) as error:
        raise B1FastLiveError(f"{field} has no raw rate/power terms") from error
    if rates.ndim != 1 or not 0 <= focal_user < rates.size:
        raise B1FastLiveError(f"{field} focal rate vector is malformed")
    focal_rate = float(rates[focal_user])
    if not np.isfinite(focal_rate) or focal_rate < 0.0:
        raise B1FastLiveError(f"{field} focal rate is invalid")
    if not np.isfinite(power) or power < 0.0:
        raise B1FastLiveError(f"{field} full power is invalid")
    return focal_rate, power


def _raw_without_focal(
    branch: object,
    actions: np.ndarray,
    rng: object,
    *,
    focal_user: int,
    offset: int,
) -> float:
    environment = _environment(branch)
    method = getattr(environment, "evaluate_actions_without_user", None)
    if not callable(method):
        raise B1FastLiveError(
            "B1 requires the non-committing evaluate_actions_without_user seam"
        )
    try:
        evaluation = method(actions, rng, focal_user=focal_user)
        power = float(getattr(evaluation, "system_power_w"))
    except Exception as error:
        raise B1FastLiveError(
            f"without-focal power evaluation failed at offset {offset}: {error}"
        ) from error
    if not np.isfinite(power) or power < 0.0:
        raise B1FastLiveError(
            f"without-focal power is invalid at successor offset {offset}"
        )
    return power


def _target_mapping(target: FocalSegmentContinuationSurplus) -> dict[str, object]:
    return {
        "schema": target.schema,
        "z2_focal_segment_surplus_bits": target.z2_focal_segment_surplus_bits,
        "successor_offsets": list(target.successor_offsets),
        "offset_surplus_bits": list(target.offset_surplus_bits),
        "offset_rate_delta_bits": list(target.offset_rate_delta_bits),
        "offset_marginal_energy_delta_j": list(target.offset_marginal_energy_delta_j),
        "candidate_focal_rates_bps": list(target.candidate_focal_rates_bps),
        "reference_focal_rates_bps": list(target.reference_focal_rates_bps),
        "candidate_focal_marginal_power_w": list(target.candidate_focal_marginal_power_w),
        "reference_focal_marginal_power_w": list(target.reference_focal_marginal_power_w),
        "candidate_full_power_w": list(target.candidate_full_power_w),
        "candidate_without_focal_power_w": list(target.candidate_without_focal_power_w),
        "reference_full_power_w": list(target.reference_full_power_w),
        "reference_without_focal_power_w": list(target.reference_without_focal_power_w),
        "lambda_bits_per_j": target.lambda_bits_per_j,
        "interval_s": target.interval_s,
    }


@dataclass(frozen=True)
class B1FastLiveCapture:
    """Raw B1 fast-screen terms plus an explicit diagnostic claim ceiling."""

    target: FocalSegmentContinuationSurplus
    tape_sha256: str
    focal_user: int
    successor_offsets: tuple[int, ...]
    candidate_modes: tuple[str, ...]
    candidate_support_counts: tuple[int, ...]
    reference_actions: tuple[tuple[int, ...], ...]
    candidate_actions: tuple[tuple[int, ...], ...]
    removal_validation_actions: tuple[int | None, ...]
    schema: str = B1_FAST_LIVE_SCHEMA
    claim_ceiling: str = B1_CLAIM_CEILING
    training_run: bool = False
    held_out_ee_evaluated: bool = False
    target_or_ee_selected: bool = False
    fallback_used: bool = False
    replacement_used: bool = False

    def __post_init__(self) -> None:
        if self.schema != B1_FAST_LIVE_SCHEMA:
            raise B1FastLiveError("B1 fast-live schema is stale")
        if self.successor_offsets != B1_SUCCESSOR_OFFSETS:
            raise B1FastLiveError("B1 fast-live offsets must be exactly (1,2,3)")
        if len(self.candidate_modes) != 3 or len(self.candidate_support_counts) != 3:
            raise B1FastLiveError("B1 fast-live mode/support receipts are incomplete")
        if len(self.reference_actions) != 3 or len(self.candidate_actions) != 3:
            raise B1FastLiveError("B1 fast-live native action receipts are incomplete")
        if len(self.removal_validation_actions) != 3:
            raise B1FastLiveError("B1 removal-validation receipt is incomplete")
        if self.fallback_used or self.replacement_used or self.training_run:
            raise B1FastLiveError("B1 fast-live diagnostic flags cannot claim fallback/training")

    @property
    def z2_focal_segment_surplus_bits(self) -> float:
        return float(self.target.z2_focal_segment_surplus_bits)

    def as_mapping(self) -> dict[str, object]:
        body: dict[str, object] = {
            "schema": self.schema,
            "claim_ceiling": self.claim_ceiling,
            "focal_user": self.focal_user,
            "successor_offsets": list(self.successor_offsets),
            "tape_sha256": self.tape_sha256,
            "candidate_modes": list(self.candidate_modes),
            "candidate_support_counts": list(self.candidate_support_counts),
            "reference_actions": [list(row) for row in self.reference_actions],
            "candidate_actions": [list(row) for row in self.candidate_actions],
            "removal_validation_actions": list(self.removal_validation_actions),
            "target": _target_mapping(self.target),
            "training_run": self.training_run,
            "held_out_ee_evaluated": self.held_out_ee_evaluated,
            "target_or_ee_selected": self.target_or_ee_selected,
            "fallback_used": self.fallback_used,
            "replacement_used": self.replacement_used,
        }
        body["capture_sha256"] = _canonical_sha256(body)
        return body


def capture_b1_pair(
    *,
    reference_branch: object,
    candidate_branch: object,
    reference_rng: object,
    candidate_rng: object,
    reference_opening_actions: object,
    candidate_opening_actions: object,
    reference_opening_physical_actions: object,
    candidate_opening_physical_actions: object,
    reference_tape: B1PhysicalActionTape | Sequence[Sequence[PhysicalAction]],
    focal_user: int,
    lambda_bits_per_j: float,
    interval_s: float,
    focal_removal_validation_action: FocalRemovalCarrier | None = None,
) -> B1FastLiveCapture:
    """Capture one matched B1 pair from two branches at the same anchor.

    ``reference_branch`` and ``candidate_branch`` must be positioned *before*
    their opening step.  ``reference_tape`` is the precommitted physical
    Q1+Q3 reference continuation at offsets 1--3.  The two branches must be
    driven by the same keyed random-field construction; the adapter accepts
    the branches as already authenticated and does not silently replace that
    provenance.

    ``focal_removal_validation_action`` is called only after the candidate
    opening key is no longer uniquely legal.  It receives
    ``(candidate_branch, current_observation, offset)`` and returns one legal
    focal native action solely so ``step_without_user`` can validate the full
    vector before removing that user.  The returned action is never executed;
    the removal seam overwrites it.  Omitting this callback when release is
    needed is a structural failure, not permission to invent a fallback.
    """

    try:
        reference_users = len(tuple(reference_opening_actions))  # type: ignore[arg-type]
    except TypeError as error:
        raise B1FastLiveError("reference opening actions are malformed") from error
    ref_opening, cand_opening, ref_opening_physical, cand_opening_physical = _opening_check(
        reference_opening_actions,
        candidate_opening_actions,
        reference_opening_physical_actions,
        candidate_opening_physical_actions,
        focal_user=focal_user,
    )
    if reference_users != len(ref_opening):
        raise B1FastLiveError("reference opening user count drifted")
    tape = _normalize_tape(reference_tape, focal_user=focal_user, users=len(ref_opening))
    held_key = cand_opening_physical[focal_user]
    assert held_key is not None

    _step(
        reference_branch,
        ref_opening,
        reference_rng,
        focal_user=focal_user,
        remove_focal=False,
        offset=0,
    )
    _step(
        candidate_branch,
        cand_opening,
        candidate_rng,
        focal_user=focal_user,
        remove_focal=False,
        offset=0,
    )

    reference_rates: list[float] = []
    candidate_rates: list[float] = []
    reference_full_power: list[float] = []
    candidate_full_power: list[float] = []
    reference_without_power: list[float] = []
    candidate_without_power: list[float] = []
    reference_actions_receipt: list[tuple[int, ...]] = []
    candidate_actions_receipt: list[tuple[int, ...]] = []
    candidate_modes: list[str] = []
    candidate_support: list[int] = []
    removal_receipt: list[int | None] = []
    released = False

    for offset, tape_row in zip(B1_SUCCESSOR_OFFSETS, tape.physical_actions, strict=True):
        reference_tables = _slot_tables(
            reference_branch,
            field=f"reference offset {offset}",
        )
        candidate_tables = _slot_tables(
            candidate_branch,
            field=f"candidate offset {offset}",
        )
        if len(reference_tables) != len(ref_opening) or len(candidate_tables) != len(ref_opening):
            raise B1FastLiveError(f"slot-table user width drifted at offset {offset}")

        # The frozen reference Q1+Q3 tape is the entire reference action
        # vector.  If any physical key is missing or duplicated, the cell is
        # structurally unsupported; no branch-local repair is permitted.
        reference_actions = _remap_reference(
            tape_row,
            reference_tables,
            field=f"reference tape offset {offset}",
        )

        hold_count = _physical_match_count(
            _table_for_user(candidate_tables, focal_user, field=f"candidate offset {offset}"),
            held_key,
        )
        candidate_support.append(hold_count)
        if not released and hold_count == 1:
            held_action = _map_one(
                held_key,
                _table_for_user(candidate_tables, focal_user, field=f"candidate offset {offset}"),
                field=f"candidate held focal key offset {offset}",
            )
            candidate_actions = _remap_candidate_nonfocal(
                tape_row,
                candidate_tables,
                focal_user=focal_user,
                focal_action=held_action,
                field=f"candidate tape offset {offset}",
            )
            mode = "hold"
            removal_receipt.append(None)
            remove_focal = False
        else:
            released = True
            if focal_removal_validation_action is None:
                raise B1FastLiveError(
                    f"candidate focal hold released at offset {offset}; "
                    "no removal validation action was provided"
                )
            observation = _observation(candidate_branch)
            try:
                carrier = focal_removal_validation_action(
                    candidate_branch,
                    observation,
                    offset,
                )
            except Exception as error:
                raise B1FastLiveError(
                    f"removal validation action failed at offset {offset}: {error}"
                ) from error
            if type(carrier) is not int or not 0 <= carrier < NUM_ACTIONS:
                raise B1FastLiveError(
                    f"removal validation action at offset {offset} is not native"
                )
            candidate_actions = _remap_candidate_nonfocal(
                tape_row,
                candidate_tables,
                focal_user=focal_user,
                focal_action=carrier,
                field=f"candidate tape offset {offset}",
            )
            mode = "removed"
            removal_receipt.append(carrier)
            remove_focal = True

        reference_without = _raw_without_focal(
            reference_branch,
            reference_actions,
            reference_rng,
            focal_user=focal_user,
            offset=offset,
        )
        candidate_without = _raw_without_focal(
            candidate_branch,
            candidate_actions,
            candidate_rng,
            focal_user=focal_user,
            offset=offset,
        )
        reference_result = _step(
            reference_branch,
            reference_actions,
            reference_rng,
            focal_user=focal_user,
            remove_focal=False,
            offset=offset,
        )
        candidate_result = _step(
            candidate_branch,
            candidate_actions,
            candidate_rng,
            focal_user=focal_user,
            remove_focal=remove_focal,
            offset=offset,
        )
        reference_outcome = _last_outcome(reference_branch, offset=offset)
        candidate_outcome = _last_outcome(candidate_branch, offset=offset)
        reference_rate, reference_power = _raw_committed(
            reference_outcome,
            focal_user=focal_user,
            field=f"reference offset {offset}",
        )
        candidate_rate, candidate_power = _raw_committed(
            candidate_outcome,
            focal_user=focal_user,
            field=f"candidate offset {offset}",
        )
        reference_rates.append(reference_rate)
        candidate_rates.append(candidate_rate)
        reference_full_power.append(reference_power)
        candidate_full_power.append(candidate_power)
        reference_without_power.append(reference_without)
        candidate_without_power.append(candidate_without)
        reference_actions_receipt.append(tuple(int(value) for value in reference_actions.tolist()))
        candidate_actions_receipt.append(tuple(int(value) for value in candidate_actions.tolist()))
        candidate_modes.append(mode)
        # Keep result variables read so a stub cannot silently return no
        # result while mutating a different branch object.
        if result_done := getattr(reference_result, "done", None):
            if offset != B1_SUCCESSOR_OFFSETS[-1] and bool(result_done):
                raise B1FastLiveError("reference branch ended before B1 horizon")
        if candidate_done := getattr(candidate_result, "done", None):
            if offset != B1_SUCCESSOR_OFFSETS[-1] and bool(candidate_done):
                raise B1FastLiveError("candidate branch ended before B1 horizon")

    target = focal_segment_continuation_target(
        lambda_bits_per_j=lambda_bits_per_j,
        interval_s=interval_s,
        candidate_focal_rates_bps=candidate_rates,
        reference_focal_rates_bps=reference_rates,
        candidate_full_power_w=candidate_full_power,
        candidate_without_focal_power_w=candidate_without_power,
        reference_full_power_w=reference_full_power,
        reference_without_focal_power_w=reference_without_power,
    )
    return B1FastLiveCapture(
        target=target,
        tape_sha256=tape.tape_sha256,
        focal_user=focal_user,
        successor_offsets=B1_SUCCESSOR_OFFSETS,
        candidate_modes=tuple(candidate_modes),
        candidate_support_counts=tuple(candidate_support),
        reference_actions=tuple(reference_actions_receipt),
        candidate_actions=tuple(candidate_actions_receipt),
        removal_validation_actions=tuple(removal_receipt),
    )


# A descriptive alias keeps the call site readable in small rapid runners.
run_b1_pair = capture_b1_pair


__all__ = [
    "B1_CLAIM_CEILING",
    "B1_FAST_LIVE_SCHEMA",
    "B1_FAST_LIVE_TAPE_SCHEMA",
    "B1_SUCCESSOR_OFFSETS",
    "B1FastLiveError",
    "B1FastLiveCapture",
    "B1PhysicalActionTape",
    "capture_b1_pair",
    "precommit_q13_nonfocal_tape",
    "run_b1_pair",
]
