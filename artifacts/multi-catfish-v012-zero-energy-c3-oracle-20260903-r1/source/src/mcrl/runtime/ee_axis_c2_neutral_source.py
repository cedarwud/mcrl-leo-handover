"""Pre-decision equal-budget neutral source for the V0.3 C2 route.

The C2 informed source is allowed to choose a departure anchor/focal user and
then either hold the incumbent or use the maximum lagged-SINR non-Main rival.
This module supplies the matched neutral arm for that source mechanism.  It
constructs an *eligible physical opportunity universe* from a sealed
pre-decision anchor and samples the requested informed budget uniformly,
without replacement.

Only information available before candidate execution is accepted here:

* anchor identity and step;
* the frozen Main/reference action;
* the current legal action-to-physical-key table;
* the sealed C2 horizon and release grammar.

The module deliberately has no target, reward, rate, power, outcome, trace, or
gate fields and never calls simulator physics.  A selected opportunity carries
exactly the ``focal_user`` and ``candidate_physical_key`` needed by the
existing ``prepare_one_candidate`` -> capture/materialize path.  The helper
``prepare_selected_c2_candidate`` is a small checked adapter for that path;
it does not forecast or execute the prepared fork.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from ..env.action_contract import Association, NO_OP_ACTION, NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_temporal_pairs import C2_NEUTRAL_SOURCE_RULE, C2_POLICY_VERSION


C2_NEUTRAL_SELECTOR_SCHEMA = "multi-catfish-mcrl-v03-c2-neutral-selector-v1"
"""Schema for a sealed C2 pre-decision neutral source selection."""

# Keep the short name parallel with the existing C1/C3 selector modules.
C2_SELECTOR_SCHEMA = C2_NEUTRAL_SELECTOR_SCHEMA

C2_INFORMED_SOURCE_RULE = "c2-hold-or-max-lagged-sinr-rival-predecision-v1"
"""Name of the informed C2 source whose budget is matched."""

C2_RELEASE_GRAMMAR = C2_POLICY_VERSION
"""The current V0.3B hold-while-legal monotone release policy version."""

C2_HORIZON_STEPS = 4
"""Matched C2 horizon: offsets 0, 1, 2, and 3."""

PhysicalKey = tuple[int, int]


class C2NeutralSourceContractError(MCRLContractError):
    """A C2 pre-decision neutral source is malformed or inadmissible."""


def _digest(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise C2NeutralSourceContractError(
            f"{field} must be a lowercase SHA-256 digest"
        )
    return value


def _exact_int(value: object, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise C2NeutralSourceContractError(
            f"{field} must be an exact integer >= {minimum}"
        )
    return value


def _action(value: object, *, field: str, allow_no_op: bool = False) -> int:
    """Validate one flat action index, optionally accepting the -1 sentinel."""

    if type(value) is not int:
        raise C2NeutralSourceContractError(f"{field} must be an exact integer")
    if allow_no_op and value == int(NO_OP_ACTION):
        return value
    if value < 0 or value >= NUM_ACTIONS:
        raise C2NeutralSourceContractError(
            f"{field} must be in [0,{NUM_ACTIONS})"
        )
    return value


def _physical_key(value: object, *, field: str) -> PhysicalKey:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or type(value[0]) is not int
        or type(value[1]) is not int
        or value[0] < 0
        or value[1] < 0
    ):
        raise C2NeutralSourceContractError(
            f"{field} must be a two-integer nonnegative physical key"
        )
    return int(value[0]), int(value[1])


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _physical_from_table(table: Any, action: int, *, field: str) -> PhysicalKey | None:
    """Resolve one legal action using only the current slot table."""

    _action(action, field=field, allow_no_op=True)
    if action == int(NO_OP_ACTION):
        return None
    if action < 0 or action >= NUM_ACTIONS:
        raise C2NeutralSourceContractError(f"{field} is outside the action space")
    mask = np.asarray(getattr(table, "mask", None))
    if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
        raise C2NeutralSourceContractError(
            f"{field} table mask must be Boolean shape ({NUM_ACTIONS},)"
        )
    if not bool(mask[action]):
        raise C2NeutralSourceContractError(f"{field} is not legal at the anchor")
    try:
        association = table.association(action)
    except Exception as error:  # pragma: no cover - defensive adapter boundary
        raise C2NeutralSourceContractError(
            f"{field} has no physical association"
        ) from error
    if not isinstance(association, Association):
        raise C2NeutralSourceContractError(f"{field} has no physical association")
    return _physical_key(
        (int(association.norad_id), int(association.cell_id)),
        field=f"{field}.physical_key",
    )


@dataclass(frozen=True)
class C2PhysicalAlternative:
    """One legal physical action in a pre-decision focal-user table."""

    action: int
    physical_key: PhysicalKey

    def verify(self) -> None:
        _exact_int(self.action, field="action")
        if self.action >= NUM_ACTIONS:
            raise C2NeutralSourceContractError("action is outside the action space")
        _physical_key(self.physical_key, field="physical_key")


@dataclass(frozen=True)
class C2PredecisionAnchor:
    """A sealed anchor/focal-user view used to form the physical universe.

    ``legal_alternatives`` must be the current opening table only.  It is not
    a forecast and must not be populated from a downstream trace.
    """

    anchor_sha256: str
    step_index: int
    focal_user: int
    reference_action: int
    reference_physical_key: PhysicalKey | None
    legal_alternatives: tuple[C2PhysicalAlternative, ...]
    horizon_steps: int = C2_HORIZON_STEPS
    release_grammar: str = C2_RELEASE_GRAMMAR

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        _exact_int(self.step_index, field="step_index")
        _exact_int(self.focal_user, field="focal_user")
        _action(self.reference_action, field="reference_action", allow_no_op=True)
        if self.reference_physical_key is None:
            raise C2NeutralSourceContractError(
                "C2 source anchors require a physical detached-Main reference"
            )
        if self.reference_action == int(NO_OP_ACTION):
            raise C2NeutralSourceContractError(
                "C2 source anchors cannot use a NO_OP detached-Main reference"
            )
        _physical_key(self.reference_physical_key, field="reference_physical_key")
        if self.horizon_steps != C2_HORIZON_STEPS:
            raise C2NeutralSourceContractError(
                f"horizon_steps must equal sealed C2 horizon {C2_HORIZON_STEPS}"
            )
        if self.release_grammar != C2_RELEASE_GRAMMAR:
            raise C2NeutralSourceContractError(
                "release_grammar is stale or unsupported"
            )
        if not self.legal_alternatives:
            raise C2NeutralSourceContractError(
                "anchor has no legal physical alternatives"
            )
        seen_actions: set[int] = set()
        seen_keys: set[PhysicalKey] = set()
        for alternative in self.legal_alternatives:
            if not isinstance(alternative, C2PhysicalAlternative):
                raise C2NeutralSourceContractError(
                    "legal_alternatives must contain C2PhysicalAlternative values"
                )
            alternative.verify()
            if alternative.action in seen_actions:
                raise C2NeutralSourceContractError(
                    "legal_alternatives contain a duplicate action"
                )
            if alternative.physical_key in seen_keys:
                raise C2NeutralSourceContractError(
                    "legal_alternatives contain a duplicate physical key"
                )
            seen_actions.add(alternative.action)
            seen_keys.add(alternative.physical_key)
            if alternative.action == self.reference_action:
                raise C2NeutralSourceContractError(
                    "legal_alternatives must exclude the reference action"
                )
            if alternative.physical_key == self.reference_physical_key:
                raise C2NeutralSourceContractError(
                    "legal_alternatives must exclude the reference physical key"
                )


@dataclass(frozen=True)
class C2PredecisionOpportunity:
    """One physical candidate that can be handed to C2 preparation.

    The record is intentionally outcome-blind.  In particular, it does not
    contain a C2 target, any rate/power value, a release offset, or a forecast
    trace.  Release is generated later by the existing prepared-fork backend.
    """

    anchor_sha256: str
    step_index: int
    focal_user: int
    reference_action: int
    reference_physical_key: PhysicalKey | None
    candidate_action: int
    candidate_physical_key: PhysicalKey
    horizon_steps: int = C2_HORIZON_STEPS
    release_grammar: str = C2_RELEASE_GRAMMAR
    source_rule: str = C2_NEUTRAL_SOURCE_RULE

    @property
    def opportunity_key(self) -> tuple[str, int, PhysicalKey]:
        """Stable identity for no-replacement sampling and deduplication."""

        return self.anchor_sha256, self.focal_user, self.candidate_physical_key

    def verify(self) -> None:
        _digest(self.anchor_sha256, field="anchor_sha256")
        _exact_int(self.step_index, field="step_index")
        _exact_int(self.focal_user, field="focal_user")
        _action(self.reference_action, field="reference_action", allow_no_op=True)
        _action(self.candidate_action, field="candidate_action")
        if self.candidate_action == self.reference_action:
            raise C2NeutralSourceContractError(
                "candidate action must differ from the reference action"
            )
        if self.reference_physical_key is None:
            raise C2NeutralSourceContractError(
                "C2 opportunities require a physical detached-Main reference"
            )
        _physical_key(self.reference_physical_key, field="reference_physical_key")
        _physical_key(self.candidate_physical_key, field="candidate_physical_key")
        if self.candidate_physical_key == self.reference_physical_key:
            raise C2NeutralSourceContractError(
                "candidate physical key must differ from the reference key"
            )
        if self.horizon_steps != C2_HORIZON_STEPS:
            raise C2NeutralSourceContractError(
                f"horizon_steps must equal sealed C2 horizon {C2_HORIZON_STEPS}"
            )
        if self.release_grammar != C2_RELEASE_GRAMMAR:
            raise C2NeutralSourceContractError(
                "release_grammar is stale or unsupported"
            )
        if not isinstance(self.source_rule, str) or not self.source_rule.strip():
            raise C2NeutralSourceContractError("source_rule must be nonempty")


@dataclass(frozen=True)
class C2SourceSelection:
    """A sealed C2 source universe and selected budget."""

    selector_schema: str
    source_rule: str
    horizon_steps: int
    release_grammar: str
    all_opportunities: tuple[C2PredecisionOpportunity, ...]
    opportunities: tuple[C2PredecisionOpportunity, ...]
    informed_budget: int
    random_seed: int | None = None

    @property
    def route(self) -> str:
        return "C2"

    @property
    def budget(self) -> int:
        return len(self.opportunities)

    @property
    def eligible_anchor_sha256s(self) -> tuple[str, ...]:
        return tuple(sorted({row.anchor_sha256 for row in self.all_opportunities}))

    @property
    def selected_anchor_sha256s(self) -> tuple[str, ...]:
        return tuple(sorted({row.anchor_sha256 for row in self.opportunities}))

    def verify(self) -> None:
        if self.selector_schema != C2_NEUTRAL_SELECTOR_SCHEMA:
            raise C2NeutralSourceContractError("unsupported C2 selector schema")
        if self.source_rule != C2_NEUTRAL_SOURCE_RULE:
            raise C2NeutralSourceContractError(
                "neutral selection must use the current C2 neutral source rule"
            )
        if self.horizon_steps != C2_HORIZON_STEPS:
            raise C2NeutralSourceContractError("selection horizon disagrees with C2")
        if self.release_grammar != C2_RELEASE_GRAMMAR:
            raise C2NeutralSourceContractError("selection release grammar is stale")
        _exact_int(self.informed_budget, field="informed_budget", minimum=1)
        if self.random_seed is not None:
            _exact_int(self.random_seed, field="random_seed")
        if not self.all_opportunities:
            raise C2NeutralSourceContractError("selection universe is empty")
        if not self.opportunities:
            raise C2NeutralSourceContractError("selection has zero budget")
        if self.budget != self.informed_budget:
            raise C2NeutralSourceContractError(
                "neutral budget does not match informed budget"
            )
        if self.budget > len(self.all_opportunities):
            raise C2NeutralSourceContractError(
                "neutral budget exceeds eligible physical universe"
            )
        all_keys: set[tuple[str, int, PhysicalKey]] = set()
        for row in self.all_opportunities:
            if not isinstance(row, C2PredecisionOpportunity):
                raise C2NeutralSourceContractError(
                    "all_opportunities contains an invalid record"
                )
            row.verify()
            if row.source_rule != C2_NEUTRAL_SOURCE_RULE:
                raise C2NeutralSourceContractError(
                    "universe row is not tagged as neutral"
                )
            if row.horizon_steps != self.horizon_steps:
                raise C2NeutralSourceContractError("universe horizon mismatch")
            if row.release_grammar != self.release_grammar:
                raise C2NeutralSourceContractError("universe release grammar mismatch")
            if row.opportunity_key in all_keys:
                raise C2NeutralSourceContractError("universe contains duplicate rows")
            all_keys.add(row.opportunity_key)
        selected_keys: set[tuple[str, int, PhysicalKey]] = set()
        for row in self.opportunities:
            row.verify()
            if row.source_rule != C2_NEUTRAL_SOURCE_RULE:
                raise C2NeutralSourceContractError("selected row is not neutral")
            if row.opportunity_key not in all_keys:
                raise C2NeutralSourceContractError(
                    "selected row is outside the sealed universe"
                )
            if row.opportunity_key in selected_keys:
                raise C2NeutralSourceContractError("selected rows repeat an opportunity")
            selected_keys.add(row.opportunity_key)

    @property
    def selection_digest(self) -> str:
        """Stable receipt digest for the pre-decision selection only."""

        self.verify()
        return _canonical_sha256(
            {
                "schema": self.selector_schema,
                "source_rule": self.source_rule,
                "horizon_steps": self.horizon_steps,
                "release_grammar": self.release_grammar,
                "informed_budget": self.informed_budget,
                "random_seed": self.random_seed,
                "universe": [row.opportunity_key for row in self.all_opportunities],
                "selected": [row.opportunity_key for row in self.opportunities],
            }
        )


def build_c2_predecision_universe(
    anchors: Iterable[C2PredecisionAnchor],
) -> tuple[C2PredecisionOpportunity, ...]:
    """Expand sealed focal-user tables into an eligible physical universe.

    The input may be in any order; output is canonically sorted.  A physical
    key is the sampling unit, and duplicate action aliases are rejected at the
    anchor boundary because the live C2 backend requires a unique physical
    mapping for ``prepare_one_candidate``.
    """

    materialized = tuple(anchors)
    rows: list[C2PredecisionOpportunity] = []
    seen_anchor_users: set[tuple[str, int]] = set()
    for anchor in materialized:
        if not isinstance(anchor, C2PredecisionAnchor):
            raise C2NeutralSourceContractError(
                "anchors must contain C2PredecisionAnchor values"
            )
        anchor.verify()
        identity = (anchor.anchor_sha256, anchor.focal_user)
        if identity in seen_anchor_users:
            raise C2NeutralSourceContractError(
                "anchor/focal-user records must be unique"
            )
        seen_anchor_users.add(identity)
        for alternative in anchor.legal_alternatives:
            rows.append(
                C2PredecisionOpportunity(
                    anchor_sha256=anchor.anchor_sha256,
                    step_index=anchor.step_index,
                    focal_user=anchor.focal_user,
                    reference_action=anchor.reference_action,
                    reference_physical_key=anchor.reference_physical_key,
                    candidate_action=alternative.action,
                    candidate_physical_key=alternative.physical_key,
                    horizon_steps=anchor.horizon_steps,
                    release_grammar=anchor.release_grammar,
                    source_rule=C2_NEUTRAL_SOURCE_RULE,
                )
            )
    rows.sort(
        key=lambda row: (
            row.anchor_sha256,
            row.step_index,
            row.focal_user,
            row.candidate_physical_key,
            row.candidate_action,
        )
    )
    if len({row.opportunity_key for row in rows}) != len(rows):
        raise C2NeutralSourceContractError("physical opportunity universe is not unique")
    for row in rows:
        row.verify()
    return tuple(rows)


def _selection_from_universe(
    universe: Sequence[C2PredecisionOpportunity],
    *,
    informed_budget: int,
    rng: np.random.Generator,
    random_seed: int | None,
) -> C2SourceSelection:
    if not isinstance(rng, np.random.Generator):
        raise C2NeutralSourceContractError("rng must be numpy.random.Generator")
    _exact_int(informed_budget, field="informed_budget", minimum=1)
    canonical = tuple(universe)
    if not canonical:
        raise C2NeutralSourceContractError("eligible physical opportunity universe is empty")
    if informed_budget > len(canonical):
        raise C2NeutralSourceContractError(
            "informed budget exceeds eligible physical opportunity universe"
        )
    for row in canonical:
        if not isinstance(row, C2PredecisionOpportunity):
            raise C2NeutralSourceContractError("universe contains an invalid record")
        row.verify()
    keys = [row.opportunity_key for row in canonical]
    if len(set(keys)) != len(keys):
        raise C2NeutralSourceContractError("universe contains duplicate opportunities")
    indices = np.asarray(
        rng.choice(len(canonical), size=informed_budget, replace=False),
        dtype=np.int64,
    ).tolist()
    selected = tuple(
        sorted(
            (canonical[int(index)] for index in indices),
            key=lambda row: (
                row.anchor_sha256,
                row.step_index,
                row.focal_user,
                row.candidate_physical_key,
                row.candidate_action,
            ),
        )
    )
    selection = C2SourceSelection(
        selector_schema=C2_NEUTRAL_SELECTOR_SCHEMA,
        source_rule=C2_NEUTRAL_SOURCE_RULE,
        horizon_steps=C2_HORIZON_STEPS,
        release_grammar=C2_RELEASE_GRAMMAR,
        all_opportunities=canonical,
        opportunities=selected,
        informed_budget=informed_budget,
        random_seed=random_seed,
    )
    selection.verify()
    return selection


def sample_c2_neutral_source(
    universe: Iterable[C2PredecisionOpportunity],
    *,
    informed_budget: int,
    rng: np.random.Generator,
    random_seed: int | None = None,
) -> C2SourceSelection:
    """Sample an equal-budget neutral C2 source without replacement.

    ``informed_budget`` must be the number of rows emitted by the matched
    informed C2 source for the same source batch.  It is a count only; no
    informed score or candidate outcome is read by this function.
    """

    canonical = tuple(universe)
    # Canonical ordering makes the same seed independent of caller iteration
    # order, while the NumPy draw remains the only random operation.
    canonical = tuple(
        sorted(
            canonical,
            key=lambda row: (
                row.anchor_sha256,
                row.step_index,
                row.focal_user,
                row.candidate_physical_key,
                row.candidate_action,
            ),
        )
    )
    return _selection_from_universe(
        canonical,
        informed_budget=informed_budget,
        rng=rng,
        random_seed=random_seed,
    )


def select_c2_neutral_source(
    anchors: Iterable[C2PredecisionAnchor],
    *,
    informed_budget: int,
    rng: np.random.Generator,
    random_seed: int | None = None,
) -> C2SourceSelection:
    """Build the physical universe from anchors and sample its neutral arm."""

    universe = build_c2_predecision_universe(anchors)
    return _selection_from_universe(
        universe,
        informed_budget=informed_budget,
        rng=rng,
        random_seed=random_seed,
    )


def predecision_anchor_from_observation(
    *,
    anchor_sha256: str,
    step_index: int,
    focal_user: int,
    reference_action: int,
    observation: Any,
    horizon_steps: int = C2_HORIZON_STEPS,
    release_grammar: str = C2_RELEASE_GRAMMAR,
) -> C2PredecisionAnchor:
    """Create one anchor view from a current observation/slot table.

    This helper is the normal bridge for the real runner.  It reads only the
    contemporaneous ``observation.candidates.slot_tables`` and never touches
    ``last_outcome``, successor observations, targets, or gate receipts.
    """

    _digest(anchor_sha256, field="anchor_sha256")
    _exact_int(step_index, field="step_index")
    _exact_int(focal_user, field="focal_user")
    _action(reference_action, field="reference_action", allow_no_op=True)
    candidates = getattr(observation, "candidates", None)
    tables = getattr(candidates, "slot_tables", None)
    if tables is None:
        raise C2NeutralSourceContractError(
            "observation lacks contemporaneous candidate slot tables"
        )
    if focal_user >= len(tables):
        raise C2NeutralSourceContractError("focal_user is outside slot tables")
    table = tables[focal_user]
    mask = np.asarray(getattr(table, "mask", None))
    if mask.dtype != np.bool_ or mask.shape != (NUM_ACTIONS,):
        raise C2NeutralSourceContractError("focal slot table mask is malformed")
    if reference_action != int(NO_OP_ACTION) and not bool(mask[reference_action]):
        raise C2NeutralSourceContractError("reference action is not legal at anchor")
    reference_key = _physical_from_table(
        table,
        reference_action,
        field="reference_action",
    )
    candidate_rows: list[C2PhysicalAlternative] = []
    for action in np.flatnonzero(mask).tolist():
        action = int(action)
        key = _physical_from_table(table, action, field=f"legal_action[{action}]")
        if key is None or action == reference_action or key == reference_key:
            continue
        candidate_rows.append(C2PhysicalAlternative(action=action, physical_key=key))
    # The backend maps a physical key back to exactly one action.  Exclude
    # aliases instead of allowing an ambiguous neutral row into preparation.
    by_key: dict[PhysicalKey, list[C2PhysicalAlternative]] = {}
    for row in candidate_rows:
        by_key.setdefault(row.physical_key, []).append(row)
    if any(len(rows) != 1 for rows in by_key.values()):
        candidate_rows = [
            rows[0] for rows in by_key.values() if len(rows) == 1
        ]
    candidate_rows.sort(key=lambda row: (row.physical_key, row.action))
    if not candidate_rows:
        raise C2NeutralSourceContractError(
            "anchor/focal user has no uniquely executable non-reference physical alternative"
        )
    anchor = C2PredecisionAnchor(
        anchor_sha256=anchor_sha256,
        step_index=step_index,
        focal_user=focal_user,
        reference_action=reference_action,
        reference_physical_key=reference_key,
        legal_alternatives=tuple(candidate_rows),
        horizon_steps=horizon_steps,
        release_grammar=release_grammar,
    )
    anchor.verify()
    return anchor


def prepare_selected_c2_candidate(
    backend: Any,
    opportunity: C2PredecisionOpportunity,
) -> Any:
    """Hand a selected opportunity to the existing C2 prepare seam.

    This adapter checks anchor identity when the backend exposes its public
    ``anchor_sha256`` property, then calls only ``prepare_one_candidate``.
    It does not run a forecast, call ``capture_temporal_anchor``, or execute a
    live step; the caller can pass the returned object to the existing
    capture/materialization helper in its required order.
    """

    if not isinstance(opportunity, C2PredecisionOpportunity):
        raise C2NeutralSourceContractError(
            "opportunity must be C2PredecisionOpportunity"
        )
    opportunity.verify()
    backend_anchor = getattr(backend, "anchor_sha256", None)
    if backend_anchor is not None and backend_anchor != opportunity.anchor_sha256:
        raise C2NeutralSourceContractError(
            "backend anchor does not match selected C2 opportunity"
        )
    prepare = getattr(backend, "prepare_one_candidate", None)
    if not callable(prepare):
        raise C2NeutralSourceContractError(
            "backend lacks prepare_one_candidate(focal_user, candidate_key)"
        )
    try:
        return prepare(
            focal_user=opportunity.focal_user,
            candidate_key=opportunity.candidate_physical_key,
            source_rule=C2_NEUTRAL_SOURCE_RULE,
        )
    except C2NeutralSourceContractError:
        raise
    except Exception as error:  # pragma: no cover - backend-specific errors
        raise C2NeutralSourceContractError(
            "existing C2 prepare_one_candidate rejected the selected opportunity"
        ) from error


# Descriptive alias for callers that name the selected source explicitly.
prepare_c2_neutral_candidate = prepare_selected_c2_candidate


__all__ = [
    "C2_HORIZON_STEPS",
    "C2_INFORMED_SOURCE_RULE",
    "C2_POLICY_VERSION",
    "C2_SELECTOR_SCHEMA",
    "C2_NEUTRAL_SELECTOR_SCHEMA",
    "C2_NEUTRAL_SOURCE_RULE",
    "C2_RELEASE_GRAMMAR",
    "C2NeutralSourceContractError",
    "C2PhysicalAlternative",
    "C2PredecisionAnchor",
    "C2PredecisionOpportunity",
    "C2SourceSelection",
    "PhysicalKey",
    "build_c2_predecision_universe",
    "predecision_anchor_from_observation",
    "prepare_c2_neutral_candidate",
    "prepare_selected_c2_candidate",
    "sample_c2_neutral_source",
    "select_c2_neutral_source",
]
