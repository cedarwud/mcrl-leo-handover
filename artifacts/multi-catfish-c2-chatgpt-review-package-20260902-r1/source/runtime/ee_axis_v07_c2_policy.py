"""Direct behavior-policy seam for V0.7 C2 source construction.

Only frozen Q1, fresh-or-zero Q2, and frozen Q3 enter the score.  The resident
legacy Q2 is never evaluated or copied.  Every nonempty user row uses one
common native mask and one direct argmax; empty rows emit the existing no-op.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_BASE_STATE_DIM
from .ee_axis_v06_c2_k1_q13 import q13_surfaces_without_q2
from .ee_axis_v07_c2_state import (
    V07_C2_Q2_STATE_DIM,
    V07_C2_Q2_STATE_SCHEMA,
    V07_C2_Q2_STATE_SCHEMA_SHA256,
)


V07_C2_POLICY_SCHEMA = "multi-catfish-mcrl-v07-c2-direct-q123-policy-v2"
V07_C2_Q2_SCOPE_ALL = "all"
V07_C2_Q2_SCOPE_MOTION_ONE = "motion-one"
V07_C2_Q2_SCOPES = (V07_C2_Q2_SCOPE_ALL, V07_C2_Q2_SCOPE_MOTION_ONE)
_RADIAL_START = EE_AXIS_BASE_STATE_DIM + NUM_ACTIONS
_RADIAL_STOP = _RADIAL_START + NUM_ACTIONS


class FreshQ2(Protocol):
    state_schema: str
    state_schema_sha256: str

    def q2_values(self, states: np.ndarray, masks: np.ndarray) -> np.ndarray: ...


@dataclass(frozen=True)
class V07C2BehaviorDecision:
    actions: np.ndarray
    q1: np.ndarray
    q2: np.ndarray
    q3: np.ndarray
    scores: np.ndarray
    masks: np.ndarray
    schema: str = V07_C2_POLICY_SCHEMA


def direct_three_surface_actions(
    *,
    q1: np.ndarray,
    q2: np.ndarray,
    q3: np.ndarray,
    masks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return the unweighted Q1+Q2+Q3 score and one masked argmax."""

    first = np.asarray(q1, dtype=np.float64)
    second = np.asarray(q2, dtype=np.float64)
    third = np.asarray(q3, dtype=np.float64)
    legal = np.asarray(masks)
    if (
        first.ndim != 2
        or first.shape[1] != NUM_ACTIONS
        or second.shape != first.shape
        or third.shape != first.shape
        or legal.shape != first.shape
        or legal.dtype != np.bool_
    ):
        raise MCRLContractError("Q1/Q2/Q3 and native masks must be matching 28-action matrices")
    if not np.all(np.isfinite(first + second + third)):
        raise MCRLContractError("direct Q1/Q2/Q3 surfaces must be finite")
    scores = first + second + third
    actions = np.full(first.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legal, axis=1)
    if bool(np.any(eligible)):
        actions[eligible] = np.argmax(
            np.where(legal[eligible], scores[eligible], -np.inf), axis=1
        )
    return actions, scores


def motion_opportunity_user(
    *,
    states_v07_c2_q2: np.ndarray,
    masks: np.ndarray,
    reference_actions: np.ndarray,
) -> int | None:
    """Select one temporally supported user from predecision geometry only.

    The score is the signed-range-rate improvement from the frozen Q1+Q3
    reference to the most approaching legal action.  Users with fewer than
    three legal actions are outside the development C2 source contract.  Ties
    choose the lowest user index, matching source generation.
    """

    states = np.asarray(states_v07_c2_q2)
    legal = np.asarray(masks)
    reference = np.asarray(reference_actions)
    if (
        states.ndim != 2
        or states.shape[1] != V07_C2_Q2_STATE_DIM
        or legal.shape != (states.shape[0], NUM_ACTIONS)
        or legal.dtype != np.bool_
        or reference.shape != (states.shape[0],)
        or not np.issubdtype(reference.dtype, np.integer)
        or not np.all(np.isfinite(states))
    ):
        raise MCRLContractError("motion-scoped Q2 inputs are malformed")
    radial = np.asarray(states[:, _RADIAL_START:_RADIAL_STOP], dtype=np.float64)
    candidates: list[tuple[int, float]] = []
    for user in np.flatnonzero(np.count_nonzero(legal, axis=1) >= 3).tolist():
        action = int(reference[user])
        if action < 0 or action >= NUM_ACTIONS or not bool(legal[user, action]):
            raise MCRLContractError("motion-scoped Q2 reference action is invalid")
        opportunity = float(radial[user, action] - np.min(radial[user, legal[user]]))
        candidates.append((int(user), opportunity))
    if not candidates:
        return None
    return min(candidates, key=lambda item: (-item[1], item[0]))[0]


def behavior_decision(
    *,
    hybrid: object,
    fresh_q2: FreshQ2 | None,
    states_v03: np.ndarray,
    states_v04_c3: np.ndarray,
    states_v07_c2_q2: np.ndarray,
    masks: np.ndarray,
    q2_user_scope: str = V07_C2_Q2_SCOPE_ALL,
) -> V07C2BehaviorDecision:
    """Evaluate a bootstrap or refreshed policy without touching legacy Q2.

    Q1 retains the sealed V0.3 state and Q3 retains its V0.4 victim-burden
    state.  Q2 alone consumes the signed-motion V0.7 state; keeping three
    explicit inputs prevents a representation fix for one objective from
    silently changing either frozen network's deployment input.
    """

    q1, q3, legal = q13_surfaces_without_q2(
        hybrid, states_v03, states_v04_c3, masks
    )
    q2_states = np.asarray(states_v07_c2_q2)
    if (
        q2_states.shape != (q1.shape[0], V07_C2_Q2_STATE_DIM)
        or not np.issubdtype(q2_states.dtype, np.floating)
        or not np.all(np.isfinite(q2_states))
    ):
        raise MCRLContractError(
            f"V0.7 Q2 state must be a finite (U,{V07_C2_Q2_STATE_DIM}) matrix"
        )
    if q2_user_scope not in V07_C2_Q2_SCOPES:
        raise MCRLContractError("unknown fresh Q2 user scope")
    if fresh_q2 is None:
        q2 = np.zeros_like(q1, dtype=np.float64)
    else:
        if (
            getattr(fresh_q2, "state_schema", None) != V07_C2_Q2_STATE_SCHEMA
            or getattr(fresh_q2, "state_schema_sha256", None)
            != V07_C2_Q2_STATE_SCHEMA_SHA256
        ):
            raise MCRLContractError("fresh Q2 state schema is stale")
        # Do not even call the Q2 boundary for empty-mask users.  This is
        # enforced here rather than delegated to one trainer implementation.
        eligible = np.any(legal, axis=1)
        q2_eligible = np.array(eligible, copy=True)
        if q2_user_scope == V07_C2_Q2_SCOPE_MOTION_ONE:
            reference_actions, _reference_scores = direct_three_surface_actions(
                q1=q1,
                q2=np.zeros_like(q1, dtype=np.float64),
                q3=q3,
                masks=legal,
            )
            selected_user = motion_opportunity_user(
                states_v07_c2_q2=q2_states,
                masks=legal,
                reference_actions=reference_actions,
            )
            q2_eligible[:] = False
            if selected_user is not None:
                q2_eligible[selected_user] = True
        q2 = np.zeros_like(q1, dtype=np.float64)
        if bool(np.any(q2_eligible)):
            evaluated = np.asarray(
                fresh_q2.q2_values(
                    np.asarray(q2_states, dtype=np.float32)[q2_eligible],
                    legal[q2_eligible],
                ),
                dtype=np.float64,
            )
            if evaluated.shape != (int(np.count_nonzero(q2_eligible)), q1.shape[1]):
                raise MCRLContractError("fresh Q2 returned a malformed surface")
            q2[q2_eligible] = evaluated
        if q2.shape != q1.shape or not np.all(np.isfinite(q2)):
            raise MCRLContractError("fresh Q2 returned a malformed surface")
        if np.any(q2[~legal] != 0.0):
            raise MCRLContractError("fresh Q2 must zero illegal action slots")
        if bool(np.any(eligible)):
            legal_count = np.count_nonzero(legal[eligible], axis=1)
            legal_mean = np.sum(q2[eligible], axis=1) / legal_count
            legal_scale = np.maximum(
                1.0, np.max(np.abs(q2[eligible]), axis=1)
            )
            if np.any(np.abs(legal_mean) > 1e-6 * legal_scale):
                raise MCRLContractError(
                    "fresh Q2 is not centered over each native legal set"
                )
    actions, scores = direct_three_surface_actions(
        q1=q1, q2=q2, q3=q3, masks=legal
    )
    return V07C2BehaviorDecision(
        actions=np.array(actions, copy=True),
        q1=np.array(q1, copy=True),
        q2=np.array(q2, copy=True),
        q3=np.array(q3, copy=True),
        scores=np.array(scores, copy=True),
        masks=np.array(legal, dtype=np.bool_, copy=True),
    )


def focal_candidate_vector(
    *,
    reference_actions: np.ndarray,
    masks: np.ndarray,
    focal_user: int,
    candidate_action: int,
) -> np.ndarray:
    """Copy a behavior vector and change exactly one legal focal action."""

    reference = np.asarray(reference_actions)
    legal = np.asarray(masks)
    if (
        reference.ndim != 1
        or legal.dtype != np.bool_
        or legal.shape != (reference.shape[0], NUM_ACTIONS)
        or not np.issubdtype(reference.dtype, np.integer)
    ):
        raise MCRLContractError("reference actions or native masks are malformed")
    if type(focal_user) is not int or not 0 <= focal_user < reference.shape[0]:
        raise MCRLContractError("focal_user is outside the behavior vector")
    if type(candidate_action) is not int or not 0 <= candidate_action < NUM_ACTIONS:
        raise MCRLContractError("candidate_action is outside the action space")
    for user, action in enumerate(reference.tolist()):
        has_legal = bool(np.any(legal[user]))
        if has_legal:
            if action == NO_OP_ACTION or not 0 <= int(action) < NUM_ACTIONS:
                raise MCRLContractError(
                    "reference action is invalid under a nonempty native mask"
                )
            if not bool(legal[user, int(action)]):
                raise MCRLContractError(
                    "reference action is illegal under its native mask"
                )
        elif action != NO_OP_ACTION:
            raise MCRLContractError(
                "empty native masks require the reference no-op"
            )
    if not bool(legal[focal_user, candidate_action]):
        raise MCRLContractError("candidate_action is illegal under the focal native mask")
    candidate = np.asarray(reference, dtype=np.int64).copy()
    candidate[focal_user] = candidate_action
    candidate.setflags(write=False)
    return candidate


__all__ = [
    "FreshQ2",
    "V07C2BehaviorDecision",
    "V07_C2_POLICY_SCHEMA",
    "behavior_decision",
    "direct_three_surface_actions",
    "focal_candidate_vector",
]
