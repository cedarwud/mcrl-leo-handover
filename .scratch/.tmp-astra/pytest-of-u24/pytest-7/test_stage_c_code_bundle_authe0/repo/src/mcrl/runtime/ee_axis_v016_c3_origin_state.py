"""Pure V0.16 C3 state with an explicit detached-reference origin view.

V0.16 is a strict successor adapter over the sealed V0.15 reference-
conditioned state.  It preserves the complete V0.15 371-dimensional vector
and inserts one action-aligned block before the V0.15 globals::

    [V0.15 action-local blocks (13 * 28),
     reference_origin_beam (28),
     V0.15 globals (7),
     V0.15 reference beam/satellite/power-gap values at c_u (3)]

The origin block is one exactly when a candidate's physical
``(norad_id, cell_id)`` key equals the focal user's detached reference key.
The three appended globals expose the already-computed V0.15 reference blocks
at that same reference action.  An all-empty focal row uses ``-1`` and gets
zeros for both the origin block and the three new globals.

This module is deliberately only a state adapter.  It does not evaluate a
branch, read a Q value or target, advance an environment, or draw randomness.
Both returned arrays are immutable and the state carries a schema-bound digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import NUM_ACTIONS, SlotTable
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_v014_q3_state import V014_Q3_ACTION_BLOCKS
from .ee_axis_v015_c3_reference_state import (
    V015_C3_REFERENCE_ACTION_BLOCKS,
    V015_C3_REFERENCE_BEAM_START,
    V015_C3_REFERENCE_GLOBAL_START,
    V015_C3_REFERENCE_POWER_GAP_START,
    V015_C3_REFERENCE_SATELLITE_START,
    V015_C3_REFERENCE_STATE_DIM,
    V015_C3_REFERENCE_STATE_SCHEMA,
    V015_C3_REFERENCE_STATE_SCHEMA_SHA256,
    encode_ee_axis_v015_c3_reference_state,
)


V016_C3_ORIGIN_ACTION_BLOCKS = (
    *V014_Q3_ACTION_BLOCKS,
    *V015_C3_REFERENCE_ACTION_BLOCKS,
    "reference_origin_beam",
)
V016_C3_ACTION_BLOCKS = V016_C3_ORIGIN_ACTION_BLOCKS
V016_C3_ORIGIN_CONTEXT_BLOCKS = ("reference_origin_beam",)
V016_C3_CONTEXT_BLOCKS = V016_C3_ORIGIN_CONTEXT_BLOCKS
V016_C3_LOCAL_FEATURES = len(V016_C3_ORIGIN_ACTION_BLOCKS)
V016_C3_GLOBAL_FEATURES = 10
V016_C3_STATE_DIM = V016_C3_LOCAL_FEATURES * NUM_ACTIONS + V016_C3_GLOBAL_FEATURES
V016_C3_STATE_SCHEMA = "multi-catfish-mcrl-v016-c3-reference-origin-state-v1"
V016_C3_STATE_SCHEMA_VERSION = 1

# The V0.15 action-local portion is 13 * 28 = 364.  Its seven globals are
# moved as a contiguous block only because the new feature is required to be
# action-aligned; their values and order are otherwise byte-for-byte stable.
V016_C3_V015_LOCAL_DIM = V015_C3_REFERENCE_GLOBAL_START
V016_C3_ORIGIN_BEAM_START = V016_C3_V015_LOCAL_DIM
V016_C3_GLOBAL_START = V016_C3_ORIGIN_BEAM_START + NUM_ACTIONS
V016_C3_V015_GLOBAL_START = V016_C3_GLOBAL_START
V016_C3_V015_GLOBAL_END = V016_C3_V015_GLOBAL_START + 7
V016_C3_REFERENCE_GLOBALS_START = V016_C3_V015_GLOBAL_END
V016_C3_REFERENCE_BEAM_GLOBAL_START = V016_C3_REFERENCE_GLOBALS_START
V016_C3_REFERENCE_SATELLITE_GLOBAL_START = (
    V016_C3_REFERENCE_BEAM_GLOBAL_START + 1
)
V016_C3_REFERENCE_POWER_GAP_GLOBAL_START = (
    V016_C3_REFERENCE_SATELLITE_GLOBAL_START + 1
)

# Explicit aliases make the two additions easy to locate without changing
# the canonical layout constants above.
V016_C3_REFERENCE_ORIGIN_BEAM_START = V016_C3_ORIGIN_BEAM_START
V016_C3_NEW_GLOBAL_START = V016_C3_REFERENCE_GLOBALS_START


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V016_C3_STATE_SCHEMA,
        "schema_version": V016_C3_STATE_SCHEMA_VERSION,
        "source_schema": V015_C3_REFERENCE_STATE_SCHEMA,
        "source_schema_sha256": V015_C3_REFERENCE_STATE_SCHEMA_SHA256,
        "source_state_dim": V015_C3_REFERENCE_STATE_DIM,
        "action_dim": NUM_ACTIONS,
        "local_feature_dim": V016_C3_LOCAL_FEATURES,
        "global_feature_dim": V016_C3_GLOBAL_FEATURES,
        "state_dim": V016_C3_STATE_DIM,
        "layout": (
            "v015-action-local-prefix-then-reference-origin-beam-then-"
            "v015-globals-then-reference-summary-globals"
        ),
        "action_blocks": list(V016_C3_ORIGIN_ACTION_BLOCKS),
        "global_features": [
            "v015-global-0",
            "v015-global-1",
            "v015-global-2",
            "v015-global-3",
            "v015-global-4",
            "v015-global-5",
            "v015-global-6",
            "reference_beam_at_reference_action",
            "reference_satellite_at_reference_action",
            "reference_power_gap_at_reference_action",
        ],
        "origin_semantics": (
            "binary-exact-physical-norad-id-and-cell-id-match-to-focal-"
            "detached-reference-action"
        ),
        "reference_summary_semantics": (
            "copy-v015-reference-beam-satellite-power-gap-blocks-at-focal-"
            "reference-action"
        ),
        "empty_reference": "minus-one-only-when-native-mask-is-empty; all-added-values-zero",
        "preservation": (
            "v015-action-local-values-and-v015-global-values-preserved-"
            "exactly"
        ),
        "time_semantics": "current-predecision-detached-reference-conditioned",
        "forbidden_inputs": [
            "q-values-or-ranks",
            "evaluate_actions",
            "outcomes",
            "targets-or-signs",
            "evaluator",
            "rng",
            "future-information",
        ],
    }


V016_C3_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()

# Canonical gate-runner spellings.  Keep the shorter names above for parity
# with the V0.15 modules, while exposing an explicit V0.16 C3-origin prefix
# for callers that bind the whole state contract by name.
V016_C3_ORIGIN_LOCAL_FEATURES = V016_C3_LOCAL_FEATURES
V016_C3_ORIGIN_GLOBAL_FEATURES = V016_C3_GLOBAL_FEATURES
V016_C3_ORIGIN_STATE_DIM = V016_C3_STATE_DIM
V016_C3_ORIGIN_STATE_SCHEMA = V016_C3_STATE_SCHEMA
V016_C3_ORIGIN_STATE_SCHEMA_SHA256 = V016_C3_STATE_SCHEMA_SHA256


class EEAxisV016C3OriginStateError(MCRLContractError):
    """The V0.16 reference-origin C3 state violates its contract."""


EEAxisV016C3OriginStateContractError = EEAxisV016C3OriginStateError


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V016_C3_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in values.ravel()],
        "masks": masks.astype(np.uint8).tolist(),
    }
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


@dataclass(frozen=True)
class EEAxisV016C3OriginStateObservation:
    """Immutable V0.16 state and the native safe action mask."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V016_C3_STATE_SCHEMA:
            raise EEAxisV016C3OriginStateError(
                "unsupported V0.16 reference-origin C3 state schema"
            )
        if self.schema_sha256 != V016_C3_STATE_SCHEMA_SHA256:
            raise EEAxisV016C3OriginStateError(
                "V0.16 reference-origin C3 state schema digest drifted"
            )
        values = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if (
            values.ndim != 2
            or values.dtype != np.dtype(np.float32)
            or values.shape[1] != V016_C3_STATE_DIM
        ):
            raise EEAxisV016C3OriginStateError(
                f"state_matrix must be float32 shape (U,{V016_C3_STATE_DIM})"
            )
        if masks.dtype != np.bool_ or masks.shape != (values.shape[0], NUM_ACTIONS):
            raise EEAxisV016C3OriginStateError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(values)):
            raise EEAxisV016C3OriginStateError(
                "V0.16 reference-origin C3 state must be finite"
            )
        if values.flags.writeable or masks.flags.writeable:
            raise EEAxisV016C3OriginStateError(
                "V0.16 reference-origin C3 state arrays must be immutable"
            )
        origin = values[:, V016_C3_ORIGIN_BEAM_START:V016_C3_GLOBAL_START]
        if np.any(origin < 0.0) or np.any(origin > 1.0):
            raise EEAxisV016C3OriginStateError(
                "reference origin beam values must lie in [0,1]"
            )
        reference_beam = values[
            :, V016_C3_REFERENCE_BEAM_GLOBAL_START
        ]
        reference_satellite = values[
            :, V016_C3_REFERENCE_SATELLITE_GLOBAL_START
        ]
        reference_gap = values[:, V016_C3_REFERENCE_POWER_GAP_GLOBAL_START]
        if (
            np.any(reference_beam < 0.0)
            or np.any(reference_beam > 1.0)
            or np.any(reference_satellite < 0.0)
            or np.any(reference_satellite > 1.0)
            or np.any(reference_gap < -1.0)
            or np.any(reference_gap > 1.0)
        ):
            raise EEAxisV016C3OriginStateError(
                "reference summary globals are outside V0.15 bounds"
            )
        actual = _matrix_sha256(values, masks)
        if actual != self.state_sha256:
            raise EEAxisV016C3OriginStateError(
                "V0.16 reference-origin C3 state digest disagrees with its arrays"
            )
        return actual


def _reference_keys(
    observation: StepObservation,
    references: object,
    masks: np.ndarray,
) -> tuple[tuple[SlotTable, ...], np.ndarray, tuple[tuple[int, int] | None, ...]]:
    """Validate the detached references and return their physical keys."""

    if not isinstance(observation, StepObservation):
        raise EEAxisV016C3OriginStateError(
            "observation must be StepObservation"
        )
    users = int(observation.num_users)
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    if len(tables) != users or any(not isinstance(table, SlotTable) for table in tables):
        raise EEAxisV016C3OriginStateError(
            "anchor slot tables disagree with user count"
        )
    raw = np.asarray(references)
    if raw.shape != (users,) or raw.dtype.kind not in "iu":
        raise EEAxisV016C3OriginStateError(
            f"reference_actions must be an integer vector of shape ({users},)"
        )

    keys: list[tuple[int, int] | None] = []
    for uid, value in enumerate(raw.tolist()):
        action = int(value)
        if action == -1:
            if np.any(masks[uid]):
                raise EEAxisV016C3OriginStateError(
                    f"reference_actions[{uid}] may be -1 only for an all-empty native row"
                )
            keys.append(None)
            continue
        if not 0 <= action < NUM_ACTIONS or not bool(masks[uid, action]):
            raise EEAxisV016C3OriginStateError(
                f"reference_actions[{uid}] is not legal under the native mask"
            )
        table = tables[uid]
        norads = np.asarray(table.norad_ids)
        cells = np.asarray(table.cell_ids)
        if (
            norads.shape != (NUM_ACTIONS,)
            or cells.shape != (NUM_ACTIONS,)
            or not np.issubdtype(norads.dtype, np.integer)
            or not np.issubdtype(cells.dtype, np.integer)
        ):
            raise EEAxisV016C3OriginStateError("anchor slot table is malformed")
        keys.append((int(norads[action]), int(cells[action])))
    return tables, np.array(raw.tolist(), dtype=np.int64, copy=True), tuple(keys)


def _origin_block(
    tables: tuple[SlotTable, ...],
    masks: np.ndarray,
    reference_keys: tuple[tuple[int, int] | None, ...],
) -> np.ndarray:
    users = len(tables)
    origin = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    for uid, table in enumerate(tables):
        reference_key = reference_keys[uid]
        if reference_key is None:
            continue
        norads = np.asarray(table.norad_ids)
        cells = np.asarray(table.cell_ids)
        for action_raw in np.flatnonzero(masks[uid]).tolist():
            action = int(action_raw)
            origin[uid, action] = np.float32(
                (int(norads[action]), int(cells[action])) == reference_key
            )
    return origin


def encode_ee_axis_v016_c3_origin_state(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    reference_actions: object,
    current_required_power_w: object,
    opening_service_feasible: object,
    interval_s: float,
    kappa_bits: float,
    pmax_w: float,
) -> EEAxisV016C3OriginStateObservation:
    """Encode the V0.15 state plus physical reference-origin features.

    The input contract is intentionally identical to
    :func:`encode_ee_axis_v015_c3_reference_state`.  The V0.15 encoder remains
    the validation and feature authority for all pre-existing 371 values.
    """

    try:
        base = encode_ee_axis_v015_c3_reference_state(
            environment,
            observation,
            reference_actions=reference_actions,
            current_required_power_w=current_required_power_w,
            opening_service_feasible=opening_service_feasible,
            interval_s=interval_s,
            kappa_bits=kappa_bits,
            pmax_w=pmax_w,
        )
    except (TypeError, ValueError, MCRLContractError) as error:
        raise EEAxisV016C3OriginStateError(
            f"V0.15 reference state cannot be encoded: {error}"
        ) from error

    try:
        base.verify()
    except (TypeError, ValueError, MCRLContractError) as error:
        raise EEAxisV016C3OriginStateError(
            "V0.15 reference state failed its own verification"
        ) from error

    old = np.asarray(base.state_matrix)
    masks = np.array(base.action_masks, dtype=np.bool_, copy=True, order="C")
    if old.ndim != 2 or old.shape[1] != V015_C3_REFERENCE_STATE_DIM:
        raise EEAxisV016C3OriginStateError(
            f"V0.15 reference state must have shape (U,{V015_C3_REFERENCE_STATE_DIM})"
        )
    tables, references, reference_keys = _reference_keys(
        observation, reference_actions, masks
    )
    origin = _origin_block(tables, masks, reference_keys)

    # The three new globals are a literal extraction from the V0.15 action
    # blocks.  In particular, they use the *focal* c_u, not a peer aggregate
    # and not a Q-selected replacement action.
    reference_globals = np.zeros((len(tables), 3), dtype=np.float32)
    for uid, reference in enumerate(references.tolist()):
        if reference == -1:
            continue
        reference_globals[uid, 0] = old[
            uid, V015_C3_REFERENCE_BEAM_START + reference
        ]
        reference_globals[uid, 1] = old[
            uid, V015_C3_REFERENCE_SATELLITE_START + reference
        ]
        reference_globals[uid, 2] = old[
            uid, V015_C3_REFERENCE_POWER_GAP_START + reference
        ]

    values = np.concatenate(
        (
            old[:, :V016_C3_V015_LOCAL_DIM],
            origin,
            old[:, V015_C3_REFERENCE_GLOBAL_START:],
            reference_globals,
        ),
        axis=1,
        dtype=np.float32,
    )
    if values.shape != (len(tables), V016_C3_STATE_DIM):
        raise EEAxisV016C3OriginStateError(
            "V0.16 reference-origin C3 state assembly has the wrong shape"
        )
    if not np.array_equal(
        values[:, :V016_C3_V015_LOCAL_DIM],
        old[:, :V016_C3_V015_LOCAL_DIM],
    ) or not np.array_equal(
        values[:, V016_C3_V015_GLOBAL_START:V016_C3_V015_GLOBAL_END],
        old[:, V015_C3_REFERENCE_GLOBAL_START:],
    ):
        raise EEAxisV016C3OriginStateError(
            "V0.15 state values changed during V0.16 assembly"
        )

    values.setflags(write=False)
    masks.setflags(write=False)
    result = EEAxisV016C3OriginStateObservation(
        schema=V016_C3_STATE_SCHEMA,
        schema_sha256=V016_C3_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    result.verify()
    return result


encode_v016_c3_origin_state = encode_ee_axis_v016_c3_origin_state


__all__ = [
    "EEAxisV016C3OriginStateContractError",
    "EEAxisV016C3OriginStateError",
    "EEAxisV016C3OriginStateObservation",
    "V016_C3_ACTION_BLOCKS",
    "V016_C3_CONTEXT_BLOCKS",
    "V016_C3_GLOBAL_FEATURES",
    "V016_C3_GLOBAL_START",
    "V016_C3_LOCAL_FEATURES",
    "V016_C3_NEW_GLOBAL_START",
    "V016_C3_ORIGIN_ACTION_BLOCKS",
    "V016_C3_ORIGIN_BEAM_START",
    "V016_C3_ORIGIN_CONTEXT_BLOCKS",
    "V016_C3_ORIGIN_GLOBAL_FEATURES",
    "V016_C3_ORIGIN_LOCAL_FEATURES",
    "V016_C3_ORIGIN_STATE_DIM",
    "V016_C3_ORIGIN_STATE_SCHEMA",
    "V016_C3_ORIGIN_STATE_SCHEMA_SHA256",
    "V016_C3_REFERENCE_BEAM_GLOBAL_START",
    "V016_C3_REFERENCE_ORIGIN_BEAM_START",
    "V016_C3_REFERENCE_GLOBALS_START",
    "V016_C3_REFERENCE_POWER_GAP_GLOBAL_START",
    "V016_C3_REFERENCE_SATELLITE_GLOBAL_START",
    "V016_C3_STATE_DIM",
    "V016_C3_STATE_SCHEMA",
    "V016_C3_STATE_SCHEMA_SHA256",
    "V016_C3_STATE_SCHEMA_VERSION",
    "V016_C3_V015_GLOBAL_END",
    "V016_C3_V015_GLOBAL_START",
    "V016_C3_V015_LOCAL_DIM",
    "encode_ee_axis_v016_c3_origin_state",
    "encode_v016_c3_origin_state",
]
