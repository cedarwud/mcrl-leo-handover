"""Read-only DROP-C2 continuation decisions for the V0.4 C2 census.

The support-complete C2 probe labels one opening intervention with a short
downstream continuation.  Its canonical label still uses detached Main, but
the preregistered robustness phase must also ask whether the action ranking is
stable when the two already-confirmed route heads, Q1 and Q3, re-decide at
each downstream state.

This module is deliberately only an inference adapter.  It creates no fourth
network, does not evaluate Q2, owns no optimizer, and does not mutate a hybrid
checkpoint.  A branch runner remains responsible for applying the focal
hold/release override after this adapter returns the common Q1+Q3 actions.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np
import torch

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_state import encode_ee_axis_state
from .ee_axis_v04_c3_state import encode_ee_axis_v04_c3_state


Q13_CONTINUATION_SCHEMA = "multi-catfish-mcrl-v04-c2-q13-continuation-v1"
Q13_SELECTED_RUNG = 100


class Q13ContinuationContractError(MCRLContractError):
    """A proposed DROP-C2 continuation is not the frozen Q1+Q3 policy."""


def _array_sha256(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        value = np.asarray(array)
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(list(value.shape), separators=(",", ":")).encode("ascii"))
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _positive(value: object, *, field: str) -> float:
    if isinstance(value, bool):
        raise Q13ContinuationContractError(f"{field} must be finite and positive")
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise Q13ContinuationContractError(
            f"{field} must be finite and positive"
        ) from error
    if not math.isfinite(converted) or converted <= 0.0:
        raise Q13ContinuationContractError(f"{field} must be finite and positive")
    return converted


@dataclass(frozen=True)
class Q13ContinuationDecision:
    """One auditable, read-only Q1+Q3 action-vector decision."""

    initialization_seed: int
    selected_q3_rung: int
    legacy_state_sha256: str
    c3_state_sha256: str
    mask_sha256: str
    q1_sha256: str
    q3_sha256: str
    actions: tuple[int, ...]
    decision_sha256: str
    schema: str = Q13_CONTINUATION_SCHEMA


def select_frozen_q13_continuation(
    trainer: Any,
    wrapped: Any,
    observation: Any,
    *,
    interval_s: float,
    kappa_bits: float,
) -> Q13ContinuationDecision:
    """Return the exact legal argmax of frozen Q1+Q3 for one branch state."""

    interval = _positive(interval_s, field="interval_s")
    kappa = _positive(kappa_bits, field="kappa_bits")
    seed = getattr(trainer, "initialization_seed", None)
    rung = getattr(trainer, "selected_q3_rung", None)
    q_nets = getattr(trainer, "q_nets", None)
    if type(seed) is not int or seed < 0:
        raise Q13ContinuationContractError("hybrid initialization seed is invalid")
    if rung != Q13_SELECTED_RUNG:
        raise Q13ContinuationContractError(
            f"DROP-C2 continuation requires selected Q3 rung {Q13_SELECTED_RUNG}"
        )
    if q_nets is None or len(q_nets) != 3:
        raise Q13ContinuationContractError(
            "DROP-C2 continuation requires exactly three resident Q networks"
        )
    if any(bool(getattr(network, "training", True)) for network in q_nets):
        raise Q13ContinuationContractError(
            "all three resident networks must be in evaluation mode"
        )
    if not callable(getattr(trainer, "q_values_by_route", None)):
        raise Q13ContinuationContractError("hybrid lacks route-local inference")

    environment = getattr(wrapped, "environment", None)
    if environment is None:
        raise Q13ContinuationContractError(
            "continuation wrapper lacks the canonical step environment"
        )
    legacy = encode_ee_axis_state(environment, observation)
    c3 = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=interval,
        kappa_bits=kappa,
    )
    legacy_state = np.asarray(legacy.state_matrix)
    c3_state = np.asarray(c3.state_matrix)
    legacy_mask = np.asarray(legacy.action_masks)
    c3_mask = np.asarray(c3.action_masks)
    if (
        legacy_state.ndim != 2
        or c3_state.shape != legacy_state.shape
        or legacy_mask.dtype != np.bool_
        or legacy_mask.shape != (legacy_state.shape[0], NUM_ACTIONS)
        or not np.array_equal(legacy_mask, c3_mask)
        or not np.all(np.any(legacy_mask, axis=1))
    ):
        raise Q13ContinuationContractError(
            "V0.3/V0.4 continuation states or common masks disagree"
        )

    with torch.no_grad():
        surfaces = trainer.q_values_by_route(legacy_state, c3_state, legacy_mask)
    if not isinstance(surfaces, tuple) or len(surfaces) != 3:
        raise Q13ContinuationContractError(
            "route-local inference must return exactly Q1, Q2, and Q3"
        )
    q1, _q2, q3 = (np.asarray(value) for value in surfaces)
    if (
        q1.shape != legacy_mask.shape
        or q3.shape != legacy_mask.shape
        or not np.all(np.isfinite(q1))
        or not np.all(np.isfinite(q3))
    ):
        raise Q13ContinuationContractError("Q1/Q3 surfaces are malformed")
    scores = q1 + q3
    if not np.all(np.isfinite(scores)):
        raise Q13ContinuationContractError("Q1+Q3 scores are non-finite")
    actions = np.full(scores.shape[0], NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(legacy_mask, axis=1)
    actions[eligible] = np.argmax(
        np.where(legacy_mask[eligible], scores[eligible], -np.inf), axis=1
    )

    payload = {
        "schema": Q13_CONTINUATION_SCHEMA,
        "initialization_seed": seed,
        "selected_q3_rung": rung,
        "legacy_state_sha256": _array_sha256(legacy_state),
        "c3_state_sha256": _array_sha256(c3_state),
        "mask_sha256": _array_sha256(legacy_mask),
        "q1_sha256": _array_sha256(q1),
        "q3_sha256": _array_sha256(q3),
        "actions": [int(value) for value in actions.tolist()],
    }
    return Q13ContinuationDecision(
        initialization_seed=seed,
        selected_q3_rung=rung,
        legacy_state_sha256=payload["legacy_state_sha256"],
        c3_state_sha256=payload["c3_state_sha256"],
        mask_sha256=payload["mask_sha256"],
        q1_sha256=payload["q1_sha256"],
        q3_sha256=payload["q3_sha256"],
        actions=tuple(payload["actions"]),
        decision_sha256=_canonical_sha256(payload),
    )


__all__ = [
    "Q13_CONTINUATION_SCHEMA",
    "Q13_SELECTED_RUNG",
    "Q13ContinuationContractError",
    "Q13ContinuationDecision",
    "select_frozen_q13_continuation",
]
