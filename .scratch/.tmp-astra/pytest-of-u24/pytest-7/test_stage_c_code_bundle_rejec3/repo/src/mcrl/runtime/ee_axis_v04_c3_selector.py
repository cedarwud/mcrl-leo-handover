"""Pre-outcome V0.4 C3 victim-burden source selection.

The selector sees only the sealed predecision observation, the committed
previous-slot victim burdens encoded by :mod:`ee_axis_v04_c3_state`, and the
frozen Main action.  It never evaluates a branch and never sees ``zeta_3``.

For each selected focal-state context the informed source keeps at most four
physical alternatives.  The bounded sibling set covers the lowest and
highest signed victim-burden changes first, then the largest remaining
absolute contrasts.  This retains both relief and pressure examples without
letting one state dominate the corpus merely because it has many actions.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import (
    Association,
    NO_OP_ACTION,
    NUM_ACTIONS,
    SlotTable,
    assert_selected_actions_valid,
)
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_BASE_STATE_DIM
from .ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_STATE_DIM,
    EE_AXIS_V04_C3_STATE_SCHEMA,
    EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
    EEAxisV04C3StateObservation,
    encode_ee_axis_v04_c3_state,
)


C3_V04_SELECTOR_SCHEMA = "multi-catfish-mcrl-v04-c3-victim-burden-selector-v1"
C3_V04_INFORMED_SOURCE_RULE = (
    "c3-victim-beam-primary-satellite-tiebreak-predecision-v1"
)
C3_V04_NEUTRAL_SOURCE_RULE = "c3-victim-burden-equal-budget-neutral-v1"
C3_V04_MAX_SIBLINGS_PER_CONTEXT = 4

PhysicalKey = tuple[int, int]


class C3V04SelectorContractError(MCRLContractError):
    """A V0.4 C3 selection violates the sealed pre-outcome contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3V04SelectorContractError(f"{field} must be lowercase SHA-256")
    return value


def _immutable(value: object, *, dtype: np.dtype, field: str) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1:
        raise C3V04SelectorContractError(f"{field} must be one-dimensional")
    try:
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise C3V04SelectorContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise C3V04SelectorContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _physical_key(table: SlotTable, action: int) -> PhysicalKey | None:
    if action == NO_OP_ACTION:
        return None
    association = table.association(action)
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _reference_actions(observation: StepObservation, value: object) -> np.ndarray:
    raw = np.asarray(value)
    if (
        raw.shape != (observation.num_users,)
        or not np.issubdtype(raw.dtype, np.integer)
        or np.issubdtype(raw.dtype, np.bool_)
    ):
        raise C3V04SelectorContractError(
            f"reference_actions must be integer shape ({observation.num_users},)"
        )
    actions = _immutable(raw, dtype=np.dtype(np.int64), field="reference_actions")
    try:
        return assert_selected_actions_valid(
            actions, observation.candidates.slot_tables
        )
    except (MCRLContractError, ValueError) as error:
        raise C3V04SelectorContractError(
            f"reference actions are not legal at the sealed anchor: {error}"
        ) from error


def _burden_blocks(
    state: EEAxisV04C3StateObservation,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(state.state_matrix)
    base = EE_AXIS_BASE_STATE_DIM
    beam = values[:, base : base + NUM_ACTIONS]
    satellite = values[:, base + 2 * NUM_ACTIONS : base + 3 * NUM_ACTIONS]
    if (
        beam.shape[1] != NUM_ACTIONS
        or satellite.shape[1] != NUM_ACTIONS
        or np.any(beam < 0.0)
        or np.any(satellite < 0.0)
    ):
        raise C3V04SelectorContractError("victim-burden blocks are malformed")
    return beam, satellite


@dataclass(frozen=True)
class C3V04UnilateralOpportunity:
    """One unevaluated unilateral action comparison."""

    anchor_sha256: str
    step_index: int
    source_rule: str
    focal_user: int
    reference_action: int
    candidate_action: int
    reference_physical_key: PhysicalKey | None
    candidate_physical_key: PhysicalKey
    reference_actions: np.ndarray
    candidate_actions: np.ndarray
    state: np.ndarray
    action_mask: np.ndarray
    reference_beam_burden: float
    candidate_beam_burden: float
    reference_satellite_burden: float
    candidate_satellite_burden: float
    # ``burden_delta`` and ``victim_pressure`` are deliberately beam-only.
    # The satellite quantities are authenticated auxiliary tie-breaks; they
    # are never added to the beam signal with an unfrozen equal weight.
    burden_delta: float
    victim_pressure: float
    satellite_burden_delta: float
    satellite_victim_pressure: float

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        if self.source_rule not in (
            C3_V04_INFORMED_SOURCE_RULE,
            C3_V04_NEUTRAL_SOURCE_RULE,
        ):
            raise C3V04SelectorContractError("source rule is stale")
        if type(self.step_index) is not int or self.step_index < 0:
            raise C3V04SelectorContractError("step_index must be nonnegative")
        if type(self.focal_user) is not int or self.focal_user < 0:
            raise C3V04SelectorContractError("focal_user must be nonnegative")
        reference = np.asarray(self.reference_actions)
        candidate = np.asarray(self.candidate_actions)
        if reference.ndim != 1 or candidate.shape != reference.shape:
            raise C3V04SelectorContractError("joint action vectors disagree")
        if self.focal_user >= reference.size:
            raise C3V04SelectorContractError("focal_user lies outside joint actions")
        if reference.flags.writeable or candidate.flags.writeable:
            raise C3V04SelectorContractError("joint action vectors must be immutable")
        if (
            type(self.reference_action) is not int
            or type(self.candidate_action) is not int
            or not 0 <= self.reference_action < NUM_ACTIONS
            or not 0 <= self.candidate_action < NUM_ACTIONS
        ):
            raise C3V04SelectorContractError("scalar action is outside action space")
        if not np.array_equal(
            np.delete(reference, self.focal_user),
            np.delete(candidate, self.focal_user),
        ):
            raise C3V04SelectorContractError("opportunity is not unilateral")
        if (
            int(reference[self.focal_user]) != self.reference_action
            or int(candidate[self.focal_user]) != self.candidate_action
        ):
            raise C3V04SelectorContractError("scalar and joint actions disagree")
        if self.reference_physical_key == self.candidate_physical_key:
            raise C3V04SelectorContractError("candidate does not change physical key")
        if (
            not isinstance(self.candidate_physical_key, tuple)
            or len(self.candidate_physical_key) != 2
            or any(type(value) is not int for value in self.candidate_physical_key)
        ):
            raise C3V04SelectorContractError("candidate physical key is malformed")
        if np.asarray(self.state).shape != (EE_AXIS_V04_C3_STATE_DIM,):
            raise C3V04SelectorContractError("opportunity state has wrong dimension")
        mask = np.asarray(self.action_mask)
        if mask.shape != (NUM_ACTIONS,) or mask.dtype != np.bool_:
            raise C3V04SelectorContractError("opportunity mask has wrong shape")
        if np.asarray(self.state).flags.writeable or mask.flags.writeable:
            raise C3V04SelectorContractError("opportunity arrays must be immutable")
        for field in (
            "reference_beam_burden",
            "candidate_beam_burden",
            "reference_satellite_burden",
            "candidate_satellite_burden",
            "victim_pressure",
            "satellite_victim_pressure",
        ):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value < 0.0:
                raise C3V04SelectorContractError(f"{field} must be finite and nonnegative")
        if not math.isfinite(float(self.burden_delta)) or not math.isfinite(
            float(self.satellite_burden_delta)
        ):
            raise C3V04SelectorContractError("burden deltas must be finite")
        reference_pressure = float(self.reference_beam_burden)
        candidate_pressure = float(self.candidate_beam_burden)
        if not math.isclose(
            float(self.burden_delta),
            candidate_pressure - reference_pressure,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise C3V04SelectorContractError("burden_delta disagrees with burden blocks")
        if not math.isclose(
            float(self.victim_pressure),
            max(reference_pressure, candidate_pressure),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise C3V04SelectorContractError("victim_pressure disagrees with burden blocks")
        if not math.isclose(
            float(self.satellite_burden_delta),
            float(self.candidate_satellite_burden)
            - float(self.reference_satellite_burden),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise C3V04SelectorContractError(
                "satellite_burden_delta disagrees with burden blocks"
            )
        if not math.isclose(
            float(self.satellite_victim_pressure),
            max(
                float(self.reference_satellite_burden),
                float(self.candidate_satellite_burden),
            ),
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise C3V04SelectorContractError(
                "satellite_victim_pressure disagrees with burden blocks"
            )


@dataclass(frozen=True)
class C3V04SourceSelection:
    """One immutable informed or equal-budget neutral C3 source plan."""

    anchor_sha256: str
    step_index: int
    source_rule: str
    state_schema: str
    state_schema_sha256: str
    state: EEAxisV04C3StateObservation
    reference_actions: np.ndarray
    eligible_focal_users: tuple[int, ...]
    selected_focal_users: tuple[int, ...]
    all_opportunities: tuple[C3V04UnilateralOpportunity, ...]
    opportunities: tuple[C3V04UnilateralOpportunity, ...]

    @property
    def budget(self) -> int:
        return len(self.opportunities)

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        if self.source_rule not in (
            C3_V04_INFORMED_SOURCE_RULE,
            C3_V04_NEUTRAL_SOURCE_RULE,
        ):
            raise C3V04SelectorContractError("selection source rule is stale")
        if self.state_schema != EE_AXIS_V04_C3_STATE_SCHEMA:
            raise C3V04SelectorContractError("selection state schema is stale")
        if self.state_schema_sha256 != EE_AXIS_V04_C3_STATE_SCHEMA_SHA256:
            raise C3V04SelectorContractError("selection state digest drifted")
        self.state.verify()
        if (
            self.state_schema != self.state.schema
            or self.state_schema_sha256 != self.state.schema_sha256
        ):
            raise C3V04SelectorContractError("selection and state lineage disagree")
        actions = np.asarray(self.reference_actions)
        if (
            actions.ndim != 1
            or actions.flags.writeable
            or actions.shape[0] != self.state.state_matrix.shape[0]
        ):
            raise C3V04SelectorContractError("reference actions must be immutable")
        if (
            not isinstance(self.eligible_focal_users, tuple)
            or not isinstance(self.selected_focal_users, tuple)
            or not self.eligible_focal_users
            or not self.opportunities
            or len(set(self.eligible_focal_users)) != len(self.eligible_focal_users)
            or len(set(self.selected_focal_users)) != len(self.selected_focal_users)
        ):
            raise C3V04SelectorContractError("selection is empty")
        if not set(self.selected_focal_users).issubset(self.eligible_focal_users):
            raise C3V04SelectorContractError("selected users are not eligible")
        universe: dict[tuple[int, int], C3V04UnilateralOpportunity] = {}
        for row in self.all_opportunities:
            row.verify()
            identity = (row.focal_user, row.candidate_action)
            if identity in universe:
                raise C3V04SelectorContractError("opportunity universe repeats")
            universe[identity] = row
            if (
                row.anchor_sha256 != self.anchor_sha256
                or row.step_index != self.step_index
                or row.source_rule != self.source_rule
                or not np.array_equal(row.reference_actions, actions)
                or not np.array_equal(
                    row.state, self.state.state_matrix[row.focal_user]
                )
                or not np.array_equal(
                    row.action_mask, self.state.action_masks[row.focal_user]
                )
            ):
                raise C3V04SelectorContractError(
                    "opportunity disagrees with sealed selection anchor"
                )
        counts: dict[int, int] = {}
        for row in self.opportunities:
            row.verify()
            identity = (row.focal_user, row.candidate_action)
            if identity not in universe or row is not universe[identity]:
                raise C3V04SelectorContractError("selected row is outside universe")
            counts[row.focal_user] = counts.get(row.focal_user, 0) + 1
        if any(count > C3_V04_MAX_SIBLINGS_PER_CONTEXT for count in counts.values()):
            raise C3V04SelectorContractError("sibling cap exceeded")
        if tuple(sorted(counts)) != tuple(sorted(self.selected_focal_users)):
            raise C3V04SelectorContractError("selected focal users disagree with rows")


def _validated_state(
    environment: StepEnvironment,
    observation: StepObservation,
    supplied: EEAxisV04C3StateObservation | None,
    *,
    interval_s: float,
    kappa_bits: float,
) -> EEAxisV04C3StateObservation:
    if not isinstance(environment, StepEnvironment):
        raise C3V04SelectorContractError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise C3V04SelectorContractError("observation must be StepObservation")
    current = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    state = current if supplied is None else supplied
    if not isinstance(state, EEAxisV04C3StateObservation):
        raise C3V04SelectorContractError("state must be V0.4 C3 state")
    state.verify()
    if (
        state.state_sha256 != current.state_sha256
        or not np.array_equal(state.action_masks, observation.masks)
    ):
        raise C3V04SelectorContractError("state does not match current sealed anchor")
    return state


def _bounded_extremes(
    rows: list[C3V04UnilateralOpportunity],
) -> tuple[C3V04UnilateralOpportunity, ...]:
    """Choose at most four signed/absolute burden contrasts deterministically."""

    ordered: list[C3V04UnilateralOpportunity] = []
    # Beam burden is the evidence-supported primary signal.  Satellite burden
    # is only a deterministic tie-break/auxiliary diversity signal.
    candidates = (
        min(
            rows,
            key=lambda row: (
                row.burden_delta,
                row.satellite_burden_delta,
                row.candidate_action,
            ),
        ),
        max(
            rows,
            key=lambda row: (
                row.burden_delta,
                row.satellite_burden_delta,
                -row.candidate_action,
            ),
        ),
        *sorted(
            rows,
            key=lambda row: (
                -abs(row.burden_delta),
                -abs(row.satellite_burden_delta),
                -row.victim_pressure,
                row.candidate_action,
            ),
        ),
    )
    seen: set[tuple[int, int]] = set()
    for row in candidates:
        identity = (row.focal_user, row.candidate_action)
        if identity in seen:
            continue
        seen.add(identity)
        ordered.append(row)
        if len(ordered) == C3_V04_MAX_SIBLINGS_PER_CONTEXT:
            break
    return tuple(ordered)


def select_v04_c3_source(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    anchor_sha256: str,
    reference_actions: object,
    interval_s: float,
    kappa_bits: float,
    max_focal_users: int | None = None,
    min_victim_pressure: float = 0.0,
    state: EEAxisV04C3StateObservation | None = None,
) -> C3V04SourceSelection | None:
    """Select bounded V0.4 C3 siblings without evaluating any outcome."""

    _digest(anchor_sha256, field="anchor_sha256")
    if max_focal_users is not None and (
        type(max_focal_users) is not int or max_focal_users <= 0
    ):
        raise C3V04SelectorContractError("max_focal_users must be positive")
    if (
        isinstance(min_victim_pressure, (bool, np.bool_))
        or not isinstance(min_victim_pressure, (int, float, np.number))
        or not math.isfinite(float(min_victim_pressure))
        or float(min_victim_pressure) < 0.0
    ):
        raise C3V04SelectorContractError("min_victim_pressure must be nonnegative")
    current = _validated_state(
        environment,
        observation,
        state,
        interval_s=interval_s,
        kappa_bits=kappa_bits,
    )
    reference = _reference_actions(observation, reference_actions)
    beam, satellite = _burden_blocks(current)
    universe: list[C3V04UnilateralOpportunity] = []
    by_user: dict[int, list[C3V04UnilateralOpportunity]] = {}
    # Rank focal users with beam evidence first.  Satellite burden is an
    # auxiliary tie-break only; it must never outrank beam victim pressure.
    user_scores: dict[int, tuple[float, float, float, float]] = {}
    for uid, table in enumerate(observation.candidates.slot_tables):
        reference_action = int(reference[uid])
        reference_key = _physical_key(table, reference_action)
        reference_beam = (
            float(beam[uid, reference_action]) if reference_key is not None else 0.0
        )
        reference_satellite = (
            float(satellite[uid, reference_action]) if reference_key is not None else 0.0
        )
        seen_keys: set[PhysicalKey] = set()
        rows: list[C3V04UnilateralOpportunity] = []
        for candidate_action in np.flatnonzero(table.mask).tolist():
            candidate_action = int(candidate_action)
            candidate_key = _physical_key(table, candidate_action)
            if (
                candidate_key is None
                or candidate_key == reference_key
                or candidate_key in seen_keys
            ):
                continue
            seen_keys.add(candidate_key)
            candidate_beam = float(beam[uid, candidate_action])
            candidate_satellite = float(satellite[uid, candidate_action])
            candidate = np.array(reference, dtype=np.int64, copy=True)
            candidate[uid] = candidate_action
            candidate.setflags(write=False)
            row = C3V04UnilateralOpportunity(
                anchor_sha256=anchor_sha256,
                step_index=int(observation.step_index),
                source_rule=C3_V04_INFORMED_SOURCE_RULE,
                focal_user=uid,
                reference_action=reference_action,
                candidate_action=candidate_action,
                reference_physical_key=reference_key,
                candidate_physical_key=candidate_key,
                reference_actions=reference,
                candidate_actions=candidate,
                state=current.state_matrix[uid],
                action_mask=current.action_masks[uid],
                reference_beam_burden=reference_beam,
                candidate_beam_burden=candidate_beam,
                reference_satellite_burden=reference_satellite,
                candidate_satellite_burden=candidate_satellite,
                burden_delta=candidate_beam - reference_beam,
                victim_pressure=max(reference_beam, candidate_beam),
                satellite_burden_delta=(
                    candidate_satellite - reference_satellite
                ),
                satellite_victim_pressure=max(
                    reference_satellite, candidate_satellite
                ),
            )
            row.verify()
            rows.append(row)
        if not rows:
            continue
        pressure = max(row.victim_pressure for row in rows)
        if pressure <= float(min_victim_pressure):
            continue
        by_user[uid] = rows
        universe.extend(rows)
        user_scores[uid] = (
            max(abs(row.burden_delta) for row in rows),
            pressure,
            max(abs(row.satellite_burden_delta) for row in rows),
            max(row.satellite_victim_pressure for row in rows),
        )
    if not by_user:
        return None
    eligible = tuple(
        sorted(
            by_user,
            key=lambda uid: (
                -user_scores[uid][0],
                -user_scores[uid][1],
                -user_scores[uid][2],
                -user_scores[uid][3],
                uid,
            ),
        )
    )
    selected_users = eligible if max_focal_users is None else eligible[:max_focal_users]
    selected = tuple(
        row
        for uid in selected_users
        for row in _bounded_extremes(by_user[uid])
    )
    plan = C3V04SourceSelection(
        anchor_sha256=anchor_sha256,
        step_index=int(observation.step_index),
        source_rule=C3_V04_INFORMED_SOURCE_RULE,
        state_schema=current.schema,
        state_schema_sha256=current.schema_sha256,
        state=current,
        reference_actions=reference,
        eligible_focal_users=eligible,
        selected_focal_users=tuple(selected_users),
        all_opportunities=tuple(
            sorted(universe, key=lambda row: (row.focal_user, row.candidate_action))
        ),
        opportunities=selected,
    )
    plan.verify()
    return plan


def sample_v04_c3_neutral_source(
    informed: C3V04SourceSelection,
    *,
    rng: np.random.Generator,
) -> C3V04SourceSelection:
    """Draw an equal-budget neutral source while preserving the sibling cap."""

    if not isinstance(informed, C3V04SourceSelection):
        raise C3V04SelectorContractError("informed must be V0.4 C3 selection")
    informed.verify()
    if not isinstance(rng, np.random.Generator):
        raise C3V04SelectorContractError("rng must be numpy.random.Generator")
    neutral_universe = tuple(
        C3V04UnilateralOpportunity(
            **{**row.__dict__, "source_rule": C3_V04_NEUTRAL_SOURCE_RULE}
        )
        for row in informed.all_opportunities
    )
    order = rng.permutation(len(neutral_universe)).tolist()
    selected: list[C3V04UnilateralOpportunity] = []
    counts: dict[int, int] = {}
    for index in order:
        row = neutral_universe[int(index)]
        if counts.get(row.focal_user, 0) >= C3_V04_MAX_SIBLINGS_PER_CONTEXT:
            continue
        row.verify()
        selected.append(row)
        counts[row.focal_user] = counts.get(row.focal_user, 0) + 1
        if len(selected) == informed.budget:
            break
    if len(selected) != informed.budget:
        raise C3V04SelectorContractError("neutral universe cannot meet informed budget")
    plan = C3V04SourceSelection(
        anchor_sha256=informed.anchor_sha256,
        step_index=informed.step_index,
        source_rule=C3_V04_NEUTRAL_SOURCE_RULE,
        state_schema=informed.state_schema,
        state_schema_sha256=informed.state_schema_sha256,
        state=informed.state,
        reference_actions=informed.reference_actions,
        eligible_focal_users=informed.eligible_focal_users,
        selected_focal_users=tuple(sorted(counts)),
        all_opportunities=neutral_universe,
        opportunities=tuple(
            sorted(selected, key=lambda row: (row.focal_user, row.candidate_action))
        ),
    )
    plan.verify()
    return plan


__all__ = [
    "C3_V04_INFORMED_SOURCE_RULE",
    "C3_V04_MAX_SIBLINGS_PER_CONTEXT",
    "C3_V04_NEUTRAL_SOURCE_RULE",
    "C3_V04_SELECTOR_SCHEMA",
    "C3V04SelectorContractError",
    "C3V04SourceSelection",
    "C3V04UnilateralOpportunity",
    "sample_v04_c3_neutral_source",
    "select_v04_c3_source",
]
