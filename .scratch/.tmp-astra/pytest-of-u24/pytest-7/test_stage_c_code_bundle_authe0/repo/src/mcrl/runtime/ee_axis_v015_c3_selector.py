"""Deterministic pre-outcome V0.15 C3 spatial-consolidation selector.

The selector is deliberately a small physical-table seam.  It receives one
sealed :class:`~mcrl.env.step.StepObservation`, its legal masks and current
candidate SINR values, plus the caller's DROP-C3 reference actions.  It emits
at most ``K`` pair proposals, with no evaluator, outcome, target, Q value, or
policy lookup.

For every user pair ``u < v`` and every exact common physical key
``(norad_id, cell_id)``, a proposal replaces the two reference actions with
the legal actions naming that key.  Proposals are ranked by the exact change
in the number of active physical beams over the whole reference joint action,
then the analogous satellite count, then the weaker user's normalized
``log1p(candidate_sinr)`` retention.  A stable physical-key/user/action tie
break and greedy user-disjoint admission make the result deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    SlotTable,
    assert_selected_actions_valid,
)
from ..env.step import StepObservation
from ..errors import MCRLContractError


V015_C3_SELECTOR_SCHEMA = "multi-catfish-mcrl-v015-c3-current-global-selector-v1"
V015_C3_SELECTOR_SOURCE_RULE = "c3-current-global-same-physical-beam-v1"
V015_C3_SOURCE_RULE = V015_C3_SELECTOR_SOURCE_RULE
V015_C3_DEFAULT_MAX_PROPOSALS = 4

PhysicalKey = tuple[int, int]


class EEAxisV015C3SelectorError(MCRLContractError):
    """A V0.15 C3 proposal violates the sealed pre-outcome contract."""


EEAxisV015C3SelectorContractError = EEAxisV015C3SelectorError
V015C3SelectorError = EEAxisV015C3SelectorError


def _exact_int(value: object, *, field: str, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise EEAxisV015C3SelectorError(f"{field} must be an exact integer")
    parsed = int(value)
    if minimum is not None and parsed < minimum:
        raise EEAxisV015C3SelectorError(
            f"{field} must be an integer >= {minimum}"
        )
    return parsed


def _physical_key(table: SlotTable, action: int) -> PhysicalKey:
    return int(table.norad_ids[action]), int(table.cell_ids[action])


def _validated_anchor(
    observation: StepObservation,
) -> tuple[tuple[SlotTable, ...], np.ndarray, np.ndarray]:
    if not isinstance(observation, StepObservation):
        raise EEAxisV015C3SelectorError("observation must be StepObservation")
    users = int(observation.num_users)
    if users <= 0:
        raise EEAxisV015C3SelectorError("observation must contain users")
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    if len(tables) != users or any(not isinstance(table, SlotTable) for table in tables):
        raise EEAxisV015C3SelectorError("observation slot tables are malformed")
    masks = np.asarray(observation.masks)
    if masks.dtype != np.bool_ or masks.shape != (users, NUM_ACTIONS):
        raise EEAxisV015C3SelectorError(
            f"observation masks must be Boolean shape ({users},{NUM_ACTIONS})"
        )
    mask_copy = np.array(masks, dtype=np.bool_, copy=True, order="C")
    for uid, table in enumerate(tables):
        norads = np.asarray(table.norad_ids)
        cells = np.asarray(table.cell_ids)
        table_mask = np.asarray(table.mask)
        if (
            norads.shape != (NUM_ACTIONS,)
            or cells.shape != (NUM_ACTIONS,)
            or table_mask.shape != (NUM_ACTIONS,)
            or table_mask.dtype != np.bool_
            or not np.issubdtype(norads.dtype, np.integer)
            or not np.issubdtype(cells.dtype, np.integer)
            or np.any(table_mask & (norads < 0))
            or np.any(table_mask & (cells < 0))
            or not np.array_equal(mask_copy[uid], table_mask)
        ):
            raise EEAxisV015C3SelectorError("observation slot table and mask disagree")
    try:
        sinr = np.asarray(observation.candidate_sinr, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise EEAxisV015C3SelectorError("candidate SINR is malformed") from error
    if (
        sinr.shape != (users, NUM_ACTIONS)
        or not np.all(np.isfinite(sinr))
        or np.any(sinr < 0.0)
    ):
        raise EEAxisV015C3SelectorError(
            "candidate SINR must be finite and nonnegative shape "
            f"({users},{NUM_ACTIONS})"
        )
    return tables, mask_copy, np.array(sinr, dtype=np.float64, copy=True, order="C")


def _validated_references(
    observation: StepObservation,
    tables: tuple[SlotTable, ...],
    value: object,
) -> np.ndarray:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise EEAxisV015C3SelectorError("reference actions are malformed") from error
    users = observation.num_users
    if (
        raw.shape != (users,)
        or not np.issubdtype(raw.dtype, np.integer)
        or np.issubdtype(raw.dtype, np.bool_)
    ):
        raise EEAxisV015C3SelectorError(
            f"reference actions must be integer shape ({users},)"
        )
    references = np.array(raw, dtype=np.int64, copy=True, order="C")
    try:
        return assert_selected_actions_valid(references, tables)
    except (MCRLContractError, TypeError, ValueError) as error:
        raise EEAxisV015C3SelectorError(
            f"reference actions are not legal at the anchor: {error}"
        ) from error


def _resolve_reference_argument(
    reference_actions: object | None,
    drop_c3_reference_actions: object | None,
) -> object:
    if reference_actions is not None and drop_c3_reference_actions is not None:
        raise EEAxisV015C3SelectorError(
            "provide reference_actions or drop_c3_reference_actions, not both"
        )
    value = (
        drop_c3_reference_actions
        if drop_c3_reference_actions is not None
        else reference_actions
    )
    if value is None:
        raise EEAxisV015C3SelectorError("DROP-C3 reference actions are required")
    return value


def _resolve_budget(max_proposals: object | None, k: object | None) -> int:
    if max_proposals is not None and k is not None:
        raise EEAxisV015C3SelectorError("provide max_proposals or k, not both")
    value = (
        V015_C3_DEFAULT_MAX_PROPOSALS
        if max_proposals is None and k is None
        else (k if max_proposals is None else max_proposals)
    )
    return _exact_int(value, field="max_proposals", minimum=0)


def _action_map(
    tables: tuple[SlotTable, ...], masks: np.ndarray
) -> tuple[dict[PhysicalKey, tuple[int, ...]], ...]:
    maps: list[dict[PhysicalKey, tuple[int, ...]]] = []
    for uid, table in enumerate(tables):
        grouped: dict[PhysicalKey, list[int]] = {}
        for raw_action in np.flatnonzero(masks[uid]).tolist():
            action = int(raw_action)
            key = _physical_key(table, action)
            grouped.setdefault(key, []).append(action)
        maps.append({key: tuple(actions) for key, actions in grouped.items()})
    return tuple(maps)


def _active_beams(keys: tuple[PhysicalKey | None, ...]) -> set[PhysicalKey]:
    return {key for key in keys if key is not None}


def _active_satellites(keys: tuple[PhysicalKey | None, ...]) -> set[int]:
    return {key[0] for key in keys if key is not None}


def _normalised_log1p_sinr(
    sinr: np.ndarray,
    mask: np.ndarray,
    user: int,
    action: int,
) -> float:
    legal = np.flatnonzero(mask[user])
    values = np.log1p(sinr[user, legal])
    best = float(np.max(values)) if values.size else 0.0
    selected = float(np.log1p(sinr[user, action]))
    if not math.isfinite(best) or not math.isfinite(selected):
        raise EEAxisV015C3SelectorError("candidate SINR retention is non-finite")
    # A zero-SINR action set has no meaningful quality denominator; all its
    # legal actions retain the full available (zero) signal by convention.
    return 1.0 if best == 0.0 else selected / best


@dataclass(frozen=True)
class V015C3Proposal:
    """One immutable, unevaluated two-user same-beam proposal."""

    u: int
    v: int
    au: int
    av: int
    key: PhysicalKey
    active_beam_reduction: int
    active_satellite_reduction: int
    normalized_log1p_sinr_u: float
    normalized_log1p_sinr_v: float
    min_normalized_log1p_sinr_retention: float
    schema: str = V015_C3_SELECTOR_SCHEMA
    source_rule: str = V015_C3_SELECTOR_SOURCE_RULE

    def __post_init__(self) -> None:
        for field in ("u", "v", "au", "av"):
            _exact_int(getattr(self, field), field=field)
        if self.u >= self.v or self.u < 0:
            raise EEAxisV015C3SelectorError("proposal user ids must satisfy 0 <= u < v")
        for field in ("au", "av"):
            if not 0 <= getattr(self, field) < NUM_ACTIONS:
                raise EEAxisV015C3SelectorError("proposal action is outside action space")
        if (
            not isinstance(self.key, tuple)
            or len(self.key) != 2
            or any(type(value) is not int or value < 0 for value in self.key)
        ):
            raise EEAxisV015C3SelectorError("proposal physical key is malformed")
        for field in ("active_beam_reduction", "active_satellite_reduction"):
            _exact_int(getattr(self, field), field=field)
        for field in (
            "normalized_log1p_sinr_u",
            "normalized_log1p_sinr_v",
            "min_normalized_log1p_sinr_retention",
        ):
            value = float(getattr(self, field))
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise EEAxisV015C3SelectorError(
                    f"{field} must be finite and in [0,1]"
                )
        if self.schema != V015_C3_SELECTOR_SCHEMA:
            raise EEAxisV015C3SelectorError("proposal schema is stale")
        if self.source_rule != V015_C3_SELECTOR_SOURCE_RULE:
            raise EEAxisV015C3SelectorError("proposal source rule is stale")
        expected = min(
            float(self.normalized_log1p_sinr_u),
            float(self.normalized_log1p_sinr_v),
        )
        if not math.isclose(
            float(self.min_normalized_log1p_sinr_retention),
            expected,
            rel_tol=0.0,
            abs_tol=1e-15,
        ):
            raise EEAxisV015C3SelectorError(
                "minimum SINR retention disagrees with user retentions"
            )

    @property
    def beam_reduction(self) -> int:
        return self.active_beam_reduction

    @property
    def satellite_reduction(self) -> int:
        return self.active_satellite_reduction

    @property
    def min_log1p_sinr_retention(self) -> float:
        return self.min_normalized_log1p_sinr_retention

    @property
    def score_components(self) -> tuple[object, ...]:
        """The complete deterministic ordering components, high priority first."""

        return (
            self.active_beam_reduction,
            self.active_satellite_reduction,
            self.min_normalized_log1p_sinr_retention,
            self.key[0],
            self.key[1],
            self.u,
            self.v,
            self.au,
            self.av,
        )

    @property
    def score(self) -> tuple[object, ...]:
        return self.score_components

    def verify(self) -> None:
        """Revalidate immutable scalar/schema invariants."""

        self.__post_init__()


def _proposal(
    *,
    user_u: int,
    user_v: int,
    action_u: int,
    action_v: int,
    key: PhysicalKey,
    reference_keys: tuple[PhysicalKey | None, ...],
    masks: np.ndarray,
    sinr: np.ndarray,
) -> V015C3Proposal:
    proposed = list(reference_keys)
    proposed[user_u] = key
    proposed[user_v] = key
    proposed_keys = tuple(proposed)
    beam_reduction = len(_active_beams(reference_keys)) - len(_active_beams(proposed_keys))
    satellite_reduction = len(_active_satellites(reference_keys)) - len(
        _active_satellites(proposed_keys)
    )
    retention_u = _normalised_log1p_sinr(sinr, masks, user_u, action_u)
    retention_v = _normalised_log1p_sinr(sinr, masks, user_v, action_v)
    return V015C3Proposal(
        u=user_u,
        v=user_v,
        au=action_u,
        av=action_v,
        key=key,
        active_beam_reduction=beam_reduction,
        active_satellite_reduction=satellite_reduction,
        normalized_log1p_sinr_u=retention_u,
        normalized_log1p_sinr_v=retention_v,
        min_normalized_log1p_sinr_retention=min(retention_u, retention_v),
    )


def select_v015_c3_proposals(
    observation: StepObservation,
    reference_actions: object | None = None,
    *,
    max_proposals: object | None = None,
    k: object | None = None,
    drop_c3_reference_actions: object | None = None,
) -> tuple[V015C3Proposal, ...]:
    """Return up to ``K`` deterministic, user-disjoint C3 proposals.

    ``reference_actions`` is intentionally caller supplied: it is the frozen
    DROP-C3 reference vector, not a Q1/Q2 lookup performed by this seam.
    ``drop_c3_reference_actions`` and ``k`` are spelling aliases for callers
    that want the route and budget explicit.
    """

    budget = _resolve_budget(max_proposals, k)
    tables, masks, sinr = _validated_anchor(observation)
    references = _validated_references(
        observation,
        tables,
        _resolve_reference_argument(reference_actions, drop_c3_reference_actions),
    )
    if budget == 0:
        return ()

    action_maps = _action_map(tables, masks)
    reference_keys: tuple[PhysicalKey | None, ...] = tuple(
        None
        if int(action) == NO_OP_ACTION
        else _physical_key(tables[uid], int(action))
        for uid, action in enumerate(references.tolist())
    )

    all_proposals: list[V015C3Proposal] = []
    users = len(tables)
    for user_u in range(users):
        for user_v in range(user_u + 1, users):
            common_keys = sorted(
                set(action_maps[user_u]).intersection(action_maps[user_v])
            )
            for key in common_keys:
                for action_u in action_maps[user_u][key]:
                    for action_v in action_maps[user_v][key]:
                        if action_u == int(references[user_u]) and action_v == int(
                            references[user_v]
                        ):
                            continue
                        all_proposals.append(
                            _proposal(
                                user_u=user_u,
                                user_v=user_v,
                                action_u=action_u,
                                action_v=action_v,
                                key=key,
                                reference_keys=reference_keys,
                                masks=masks,
                                sinr=sinr,
                            )
                        )

    if not all_proposals:
        return ()

    ordered = sorted(
        all_proposals,
        key=lambda item: (
            -item.active_beam_reduction,
            -item.active_satellite_reduction,
            -item.min_normalized_log1p_sinr_retention,
            item.key[0],
            item.key[1],
            item.u,
            item.v,
            item.au,
            item.av,
        ),
    )
    selected: list[V015C3Proposal] = []
    used_users: set[int] = set()
    for item in ordered:
        if item.u in used_users or item.v in used_users:
            continue
        selected.append(item)
        used_users.update((item.u, item.v))
        if len(selected) >= budget:
            break
    return tuple(selected)


select_v015_c3_pairs = select_v015_c3_proposals
select_ee_axis_v015_c3_proposals = select_v015_c3_proposals


__all__ = [
    "EEAxisV015C3SelectorContractError",
    "EEAxisV015C3SelectorError",
    "PhysicalKey",
    "V015C3Proposal",
    "V015_C3_DEFAULT_MAX_PROPOSALS",
    "V015_C3_SELECTOR_SCHEMA",
    "V015_C3_SELECTOR_SOURCE_RULE",
    "V015_C3_SOURCE_RULE",
    "select_ee_axis_v015_c3_proposals",
    "select_v015_c3_pairs",
    "select_v015_c3_proposals",
]
