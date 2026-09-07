"""Pre-decision source selectors for the V0.3 C3 route.

The C3 Catfish is a *source construction* rule.  It chooses a sealed anchor,
focal user, and physical alternatives from information that was committed in
the previous slot; it does not evaluate a candidate branch and it does not
look at a target.  The actual opening comparison is deliberately left to
``ee_axis_opening_source``.

The informed rule ranks a user's legal physical alternatives by the
action-aligned V0.3 context blocks

``eligible served load, previous beam active, previous satellite active,
maximum required link power``.

All alternatives of each selected focal user are then enumerated.  The
neutral replacement samples the same number of sealed unilateral
opportunities uniformly from the eligible universe, using a caller-supplied
generator.  Neither path contains a rate, power, target, reward, or outcome
field.  This is important: selecting an action because its ``zeta_3`` is
large would make the source an outcome filter rather than a Catfish.
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
from .ee_axis_state import (
    EE_AXIS_BASE_STATE_DIM,
    EE_AXIS_CONTEXT_BLOCKS,
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    EEAxisStateObservation,
    encode_ee_axis_state,
)


C3_SELECTOR_SCHEMA = "multi-catfish-mcrl-v03-c3-predecision-selector-v1"
"""Schema for an informed or neutral C3 source selection plan."""

C3_INFORMED_SOURCE_RULE = "c3-lagged-competitive-load-predecision-v1"
"""The V0.3 informed C3 source rule."""

C3_NEUTRAL_SOURCE_RULE = "c3-equal-budget-uniform-predecision-v1"
"""The equal-budget neutral replacement for C3."""

PhysicalKey = tuple[int, int]


class C3SelectorContractError(MCRLContractError):
    """A proposed C3 source selection violates the pre-decision contract."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C3SelectorContractError(f"{field} must be lowercase SHA-256")
    return value


def _immutable_array(
    value: object,
    *,
    field: str,
    dtype: np.dtype,
    ndim: int,
) -> np.ndarray:
    try:
        array = np.asarray(value)
        if array.ndim != ndim:
            raise C3SelectorContractError(f"{field} must be {ndim}-dimensional")
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except C3SelectorContractError:
        raise
    except (TypeError, ValueError) as error:
        raise C3SelectorContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise C3SelectorContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise C3SelectorContractError(f"{field} must be a nonempty trimmed string")
    return value


def _physical_key(table: SlotTable, action: int) -> PhysicalKey | None:
    """Return the physical association named by one legal action."""

    if action == NO_OP_ACTION:
        return None
    association = table.association(action)
    if not isinstance(association, Association):
        return None
    return int(association.norad_id), int(association.cell_id)


def _action_vector(
    value: object, *, field: str, num_users: int
) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != 1 or array.shape != (num_users,):
        raise C3SelectorContractError(f"{field} must have shape ({num_users},)")
    if (
        not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise C3SelectorContractError(f"{field} must have integer dtype")
    return _immutable_array(
        array, field=field, dtype=np.dtype(np.int64), ndim=1
    )


def _state_context(
    state: EEAxisStateObservation,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract and validate the four action-aligned lagged C3 blocks."""

    if not isinstance(state, EEAxisStateObservation):
        raise C3SelectorContractError(
            "state must be the versioned EEAxisStateObservation"
        )
    try:
        state.verify()
    except MCRLContractError as error:
        raise C3SelectorContractError(str(error)) from error
    values = np.asarray(state.state_matrix)
    if values.ndim != 2 or values.shape[1] != EE_AXIS_STATE_DIM:
        raise C3SelectorContractError("state has the wrong V0.3 dimension")
    base = EE_AXIS_BASE_STATE_DIM
    blocks = tuple(
        values[:, base + index * NUM_ACTIONS : base + (index + 1) * NUM_ACTIONS]
        for index in range(len(EE_AXIS_CONTEXT_BLOCKS))
    )
    if any(block.shape[1] != NUM_ACTIONS for block in blocks):
        raise C3SelectorContractError("state context blocks are not action aligned")
    for name, block in zip(EE_AXIS_CONTEXT_BLOCKS, blocks, strict=True):
        if not np.all(np.isfinite(block)):
            raise C3SelectorContractError(f"{name} block is not finite")
        if np.any(block < 0.0) or np.any(block > 1.0):
            raise C3SelectorContractError(
                f"{name} block must use the V0.3 normalized [0,1] range"
            )
    return blocks  # type: ignore[return-value]


def _score(
    *,
    load: float,
    beam_active: float,
    satellite_active: float,
    power: float,
) -> float:
    """Equal-weight normalized pre-decision competitive score.

    All four inputs are already normalized by the state schema.  Equal
    weighting keeps the source rule parameter-free and makes its ranking
    auditable; the score is not a reward and is never sent to a Q update.
    """

    result = float(load + beam_active + satellite_active + power)
    if not math.isfinite(result):  # defensive; blocks were checked above
        raise C3SelectorContractError("competitive score is not finite")
    return result


def _same_action_vector(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.array_equal(np.asarray(left), np.asarray(right)))


@dataclass(frozen=True)
class C3UnilateralOpportunity:
    """One sealed unilateral physical alternative.

    The record intentionally contains no evaluated rates, power, ``zeta``, or
    reward.  It can therefore be constructed before a candidate branch is
    sent to the canonical opening evaluator.
    """

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
    lagged_eligible_load: float
    previous_beam_active: bool
    previous_satellite_active: bool
    previous_max_required_link_power: float
    competitive_score: float

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        _text(self.source_rule, field="source_rule")
        if type(self.step_index) is not int or self.step_index < 0:
            raise C3SelectorContractError("step_index must be a nonnegative integer")
        if type(self.focal_user) is not int or self.focal_user < 0:
            raise C3SelectorContractError("focal_user must be a nonnegative integer")
        for field in ("reference_action", "candidate_action"):
            if type(getattr(self, field)) is not int:
                raise C3SelectorContractError(f"{field} must be an exact integer")
        if self.candidate_physical_key is None:
            raise C3SelectorContractError("C3 candidates must name a physical key")
        if self.reference_physical_key == self.candidate_physical_key:
            raise C3SelectorContractError(
                "C3 candidate must change the focal physical association"
            )
        reference = np.asarray(self.reference_actions)
        candidate = np.asarray(self.candidate_actions)
        if reference.ndim != 1 or candidate.shape != reference.shape:
            raise C3SelectorContractError("joint action vectors disagree")
        if self.focal_user >= reference.size:
            raise C3SelectorContractError("focal_user lies outside joint actions")
        if not np.issubdtype(reference.dtype, np.integer) or not np.issubdtype(
            candidate.dtype, np.integer
        ):
            raise C3SelectorContractError("joint action vectors must be integer")
        if not _same_action_vector(
            np.delete(reference, self.focal_user),
            np.delete(candidate, self.focal_user),
        ):
            raise C3SelectorContractError(
                "C3 candidate must differ only in the focal user's action"
            )
        if (
            int(reference[self.focal_user]) != self.reference_action
            or int(candidate[self.focal_user]) != self.candidate_action
        ):
            raise C3SelectorContractError(
                "scalar and joint focal actions disagree"
            )
        state = np.asarray(self.state)
        mask = np.asarray(self.action_mask)
        if state.ndim != 1 or state.size != EE_AXIS_STATE_DIM:
            raise C3SelectorContractError("opportunity state has the wrong dimension")
        if mask.ndim != 1 or mask.size != NUM_ACTIONS or mask.dtype != np.bool_:
            raise C3SelectorContractError("opportunity mask has the wrong shape")
        if state.flags.writeable or mask.flags.writeable:
            raise C3SelectorContractError("opportunity arrays must be immutable")
        for field in (
            "lagged_eligible_load",
            "previous_max_required_link_power",
            "competitive_score",
        ):
            value = float(getattr(self, field))
            if not math.isfinite(value) or not 0.0 <= value <= 4.0:
                raise C3SelectorContractError(f"{field} is outside its normalized range")


@dataclass(frozen=True)
class C3SourceSelection:
    """A sealed informed C3 plan for one pre-decision anchor."""

    anchor_sha256: str
    step_index: int
    source_rule: str
    state_schema: str
    state_schema_sha256: str
    state: EEAxisStateObservation
    reference_actions: np.ndarray
    eligible_focal_users: tuple[int, ...]
    selected_focal_users: tuple[int, ...]
    all_opportunities: tuple[C3UnilateralOpportunity, ...]
    opportunities: tuple[C3UnilateralOpportunity, ...]
    anchor_competitive_score: float

    @property
    def budget(self) -> int:
        """Number of informed rows, used by the equal-budget neutral source."""

        return len(self.opportunities)

    @property
    def route(self) -> str:
        return "C3"

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        _text(self.source_rule, field="source_rule")
        if self.state_schema != EE_AXIS_STATE_SCHEMA:
            raise C3SelectorContractError("selection state schema is stale")
        if self.state_schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise C3SelectorContractError("selection state schema digest drifted")
        self.state.verify()
        actions = np.asarray(self.reference_actions)
        if actions.ndim != 1:
            raise C3SelectorContractError("reference_actions must be one-dimensional")
        if actions.flags.writeable:
            raise C3SelectorContractError("reference_actions must be immutable")
        if type(self.step_index) is not int or self.step_index < 0:
            raise C3SelectorContractError("step_index must be a nonnegative integer")
        if not self.eligible_focal_users:
            raise C3SelectorContractError("selection has no eligible focal users")
        if not set(self.selected_focal_users).issubset(self.eligible_focal_users):
            raise C3SelectorContractError("selected users are not eligible")
        if not self.opportunities:
            raise C3SelectorContractError("selection has no unilateral opportunities")
        all_ids = {id(item) for item in self.all_opportunities}
        if any(id(item) not in all_ids for item in self.opportunities):
            raise C3SelectorContractError("selected opportunity is outside the sealed universe")
        for opportunity in self.all_opportunities:
            opportunity.verify()
            if opportunity.anchor_sha256 != self.anchor_sha256:
                raise C3SelectorContractError("opportunity anchor digest disagrees")
            if opportunity.step_index != self.step_index:
                raise C3SelectorContractError("opportunity step disagrees")
            if not _same_action_vector(opportunity.reference_actions, actions):
                raise C3SelectorContractError("opportunity reference vector disagrees")
        selected_users = tuple(op.focal_user for op in self.opportunities)
        if any(uid not in self.selected_focal_users for uid in selected_users):
            raise C3SelectorContractError("opportunity user is not selected")
        if not math.isfinite(float(self.anchor_competitive_score)):
            raise C3SelectorContractError("anchor competitive score is not finite")


def _validated_state(
    environment: StepEnvironment,
    observation: StepObservation,
    supplied: EEAxisStateObservation | None,
) -> EEAxisStateObservation:
    if not isinstance(environment, StepEnvironment):
        raise C3SelectorContractError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise C3SelectorContractError("observation must be StepObservation")
    current = encode_ee_axis_state(environment, observation)
    state = current if supplied is None else supplied
    if not isinstance(state, EEAxisStateObservation):
        raise C3SelectorContractError("state must be EEAxisStateObservation")
    state.verify()
    if state.state_matrix.shape[0] != observation.num_users:
        raise C3SelectorContractError("state and observation user counts disagree")
    if not np.array_equal(state.action_masks, observation.masks):
        raise C3SelectorContractError("state masks disagree with sealed observation")
    if state.state_sha256 != current.state_sha256:
        raise C3SelectorContractError(
            "state does not match the current sealed predecision anchor"
        )
    return state


def _validate_reference(
    observation: StepObservation,
    reference_actions: object,
) -> np.ndarray:
    actions = _action_vector(
        reference_actions,
        field="reference_actions",
        num_users=observation.num_users,
    )
    try:
        return assert_selected_actions_valid(actions, observation.candidates.slot_tables)
    except (MCRLContractError, ValueError) as error:
        raise C3SelectorContractError(
            f"reference actions are not legal at the sealed anchor: {error}"
        ) from error


def _opportunity_universe(
    *,
    observation: StepObservation,
    state: EEAxisStateObservation,
    reference: np.ndarray,
    anchor_sha256: str,
    source_rule: str,
    min_competitive_score: float,
) -> tuple[tuple[int, ...], tuple[C3UnilateralOpportunity, ...], dict[int, float]]:
    load, beam, satellite, power = _state_context(state)
    users = observation.num_users
    eligible_users: list[int] = []
    user_scores: dict[int, float] = {}
    universe: list[C3UnilateralOpportunity] = []
    for focal_user, table in enumerate(observation.candidates.slot_tables):
        valid_actions = [
            int(action)
            for action in np.flatnonzero(table.mask).tolist()
            if _physical_key(table, int(action)) is not None
        ]
        physical_keys = {
            _physical_key(table, action) for action in valid_actions
        }
        physical_keys.discard(None)
        # "Multiple physical alternatives" counts physical identities, not
        # the NO_OP sentinel or an accidental duplicate action slot.
        if len(physical_keys) < 2:
            continue
        reference_key = _physical_key(table, int(reference[focal_user]))
        reference_score = 0.0
        if reference_key is not None:
            reference_action = int(reference[focal_user])
            reference_score = _score(
                load=float(load[focal_user, reference_action]),
                beam_active=float(beam[focal_user, reference_action]),
                satellite_active=float(satellite[focal_user, reference_action]),
                power=float(power[focal_user, reference_action]),
            )

        rows: list[C3UnilateralOpportunity] = []
        for candidate_action in valid_actions:
            candidate_key = _physical_key(table, candidate_action)
            assert candidate_key is not None
            if candidate_key == reference_key:
                continue
            candidate_score = _score(
                load=float(load[focal_user, candidate_action]),
                beam_active=float(beam[focal_user, candidate_action]),
                satellite_active=float(satellite[focal_user, candidate_action]),
                power=float(power[focal_user, candidate_action]),
            )
            candidate = np.array(reference, dtype=np.int64, copy=True)
            candidate[focal_user] = candidate_action
            candidate.setflags(write=False)
            row = C3UnilateralOpportunity(
                anchor_sha256=anchor_sha256,
                step_index=int(observation.step_index),
                source_rule=source_rule,
                focal_user=focal_user,
                reference_action=int(reference[focal_user]),
                candidate_action=candidate_action,
                reference_physical_key=reference_key,
                candidate_physical_key=candidate_key,
                reference_actions=reference,
                candidate_actions=candidate,
                state=state.state_matrix[focal_user],
                action_mask=state.action_masks[focal_user],
                lagged_eligible_load=float(load[focal_user, candidate_action]),
                previous_beam_active=bool(beam[focal_user, candidate_action]),
                previous_satellite_active=bool(satellite[focal_user, candidate_action]),
                previous_max_required_link_power=float(
                    power[focal_user, candidate_action]
                ),
                competitive_score=candidate_score,
            )
            row.verify()
            rows.append(row)

        # A user qualifies only when at least one physical unilateral change
        # can be emitted and the sealed context has a competitive signal.
        if not rows:
            continue
        user_score = max(
            [reference_score, *[row.competitive_score for row in rows]]
        )
        if user_score <= min_competitive_score:
            continue
        eligible_users.append(focal_user)
        user_scores[focal_user] = user_score
        universe.extend(rows)

    # Action index is the final deterministic tie-break.  It does not encode
    # a preference and no outcome is consulted here.
    universe.sort(key=lambda row: (-row.competitive_score, row.focal_user, row.candidate_action))
    eligible_users.sort(key=lambda uid: (-user_scores[uid], uid))
    return tuple(eligible_users), tuple(universe), user_scores


def select_c3_source(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    anchor_sha256: str,
    reference_actions: object,
    max_focal_users: int | None = None,
    min_competitive_score: float = 0.0,
    state: EEAxisStateObservation | None = None,
) -> C3SourceSelection | None:
    """Select one deterministic informed C3 plan at a sealed anchor.

    ``None`` means the pre-decision anchor has no qualifying user: fewer than
    two physical alternatives, no unilateral physical change, or no positive
    lagged competitive signal.  This function never runs candidate physics.
    ``max_focal_users`` limits only the ranked focal-user prefix; all legal
    physical alternatives of each selected user are emitted.
    """

    _digest(anchor_sha256, field="anchor_sha256")
    if isinstance(min_competitive_score, (bool, np.bool_)) or not isinstance(
        min_competitive_score, (int, float, np.number)
    ):
        raise C3SelectorContractError("min_competitive_score must be finite")
    threshold = float(min_competitive_score)
    if not math.isfinite(threshold) or threshold < 0.0 or threshold >= 4.0:
        raise C3SelectorContractError(
            "min_competitive_score must be finite in [0,4)"
        )
    if max_focal_users is not None and (
        type(max_focal_users) is not int or max_focal_users <= 0
    ):
        raise C3SelectorContractError("max_focal_users must be a positive integer")
    current_state = _validated_state(environment, observation, state)
    reference = _validate_reference(observation, reference_actions)
    eligible, universe, user_scores = _opportunity_universe(
        observation=observation,
        state=current_state,
        reference=reference,
        anchor_sha256=anchor_sha256,
        source_rule=C3_INFORMED_SOURCE_RULE,
        min_competitive_score=threshold,
    )
    if not eligible or not universe:
        return None
    selected_users = eligible if max_focal_users is None else eligible[:max_focal_users]
    selected_set = set(selected_users)
    selected = tuple(
        row for row in universe if row.focal_user in selected_set
    )
    if not selected:
        return None
    plan = C3SourceSelection(
        anchor_sha256=anchor_sha256,
        step_index=int(observation.step_index),
        source_rule=C3_INFORMED_SOURCE_RULE,
        state_schema=current_state.schema,
        state_schema_sha256=current_state.schema_sha256,
        state=current_state,
        reference_actions=reference,
        eligible_focal_users=eligible,
        selected_focal_users=tuple(selected_users),
        all_opportunities=universe,
        opportunities=selected,
        anchor_competitive_score=max(user_scores.values()),
    )
    plan.verify()
    return plan


def sample_c3_neutral_source(
    informed: C3SourceSelection,
    *,
    rng: np.random.Generator,
) -> C3SourceSelection:
    """Uniformly sample an equal-budget neutral C3 plan.

    Sampling is without replacement from the full sealed opportunity universe
    and uses no score.  The returned plan has exactly the informed budget and
    keeps the same state, reference actions, anchor digest, and schema.  Its
    route provenance is the neutral rule, so it cannot be mistaken for an
    informed row downstream.
    """

    if not isinstance(informed, C3SourceSelection):
        raise C3SelectorContractError("informed must be C3SourceSelection")
    informed.verify()
    if not isinstance(rng, np.random.Generator):
        raise C3SelectorContractError("rng must be numpy.random.Generator")
    budget = informed.budget
    universe = informed.all_opportunities
    if budget <= 0:
        raise C3SelectorContractError("cannot sample a zero-budget neutral source")
    if budget > len(universe):
        raise C3SelectorContractError("neutral budget exceeds sealed opportunity universe")

    # choice is the only random operation.  Sorting the selected rows again
    # makes serialization independent of NumPy's returned index order.
    indices = rng.choice(len(universe), size=budget, replace=False)
    neutral_universe = tuple(
        C3UnilateralOpportunity(
            **{
                **row.__dict__,
                "source_rule": C3_NEUTRAL_SOURCE_RULE,
            }
        )
        for row in universe
    )
    neutral_rows = tuple(
        sorted(
            (neutral_universe[int(index)] for index in np.asarray(indices).tolist()),
            key=lambda row: (row.focal_user, row.candidate_action),
        )
    )
    for row in neutral_rows:
        row.verify()
    neutral = C3SourceSelection(
        anchor_sha256=informed.anchor_sha256,
        step_index=informed.step_index,
        source_rule=C3_NEUTRAL_SOURCE_RULE,
        state_schema=informed.state_schema,
        state_schema_sha256=informed.state_schema_sha256,
        state=informed.state,
        reference_actions=informed.reference_actions,
        eligible_focal_users=informed.eligible_focal_users,
        selected_focal_users=tuple(sorted({row.focal_user for row in neutral_rows})),
        all_opportunities=neutral_universe,
        opportunities=neutral_rows,
        anchor_competitive_score=informed.anchor_competitive_score,
    )
    neutral.verify()
    return neutral


class C3SourceSelector:
    """Convenience object for repeated informed/neutral source selection."""

    def __init__(
        self,
        *,
        max_focal_users: int | None = None,
        min_competitive_score: float = 0.0,
    ) -> None:
        if max_focal_users is not None and (
            type(max_focal_users) is not int or max_focal_users <= 0
        ):
            raise C3SelectorContractError("max_focal_users must be a positive integer")
        if isinstance(min_competitive_score, (bool, np.bool_)) or not isinstance(
            min_competitive_score, (int, float, np.number)
        ):
            raise C3SelectorContractError("min_competitive_score must be finite")
        threshold = float(min_competitive_score)
        if not math.isfinite(threshold) or threshold < 0.0 or threshold >= 4.0:
            raise C3SelectorContractError(
                "min_competitive_score must be finite in [0,4)"
            )
        self.max_focal_users = max_focal_users
        self.min_competitive_score = threshold

    def select(
        self,
        environment: StepEnvironment,
        observation: StepObservation,
        *,
        anchor_sha256: str,
        reference_actions: object,
        state: EEAxisStateObservation | None = None,
    ) -> C3SourceSelection | None:
        return select_c3_source(
            environment,
            observation,
            anchor_sha256=anchor_sha256,
            reference_actions=reference_actions,
            max_focal_users=self.max_focal_users,
            min_competitive_score=self.min_competitive_score,
            state=state,
        )

    @staticmethod
    def neutral(
        informed: C3SourceSelection,
        *,
        rng: np.random.Generator,
    ) -> C3SourceSelection:
        return sample_c3_neutral_source(informed, rng=rng)


__all__ = [
    "C3_INFORMED_SOURCE_RULE",
    "C3_NEUTRAL_SOURCE_RULE",
    "C3_SELECTOR_SCHEMA",
    "C3SelectorContractError",
    "C3SourceSelection",
    "C3SourceSelector",
    "C3UnilateralOpportunity",
    "PhysicalKey",
    "sample_c3_neutral_source",
    "select_c3_source",
]
