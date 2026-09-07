"""Deployable V0.15 C3 state with current global spatial context.

V0.15 keeps the immutable V0.14 287-dimensional ZR-Q3 state and appends two
action-aligned blocks derived from the sealed current candidate tables:

``current_same_beam_user_fraction``
    Fraction of non-focal users that have at least one *legal* action for the
    exact ``(norad_id, cell_id)`` represented by this action.

``current_same_satellite_user_fraction``
    Fraction of non-focal users that have at least one legal action on the
    represented satellite.

Each other user contributes at most once to either fraction, even when its
candidate table contains repeated slots for the same physical identity.  The
encoder never reads an outcome, Q value, selected action, target, evaluator,
or RNG.  The returned state and mask are immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import NUM_ACTIONS, SlotTable
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_v014_q3_state import (
    EEAxisV014Q3StateObservation,
    V014_Q3_GLOBAL_FEATURES,
    V014_Q3_LOCAL_FEATURES,
    V014_Q3_STATE_DIM,
    V014_Q3_STATE_SCHEMA,
    V014_Q3_STATE_SCHEMA_SHA256,
    encode_ee_axis_v014_q3_state,
)


V015_C3_ACTION_BLOCKS = (
    "current_same_beam_user_fraction",
    "current_same_satellite_user_fraction",
)
V015_C3_CONTEXT_BLOCKS = V015_C3_ACTION_BLOCKS
V015_C3_STATE_SCHEMA = "multi-catfish-mcrl-v015-c3-current-global-spatial-state-v1"
V015_C3_STATE_SCHEMA_VERSION = 1
V015_C3_STATE_DIM = V014_Q3_STATE_DIM + len(V015_C3_ACTION_BLOCKS) * NUM_ACTIONS
V015_C3_LOCAL_FEATURES = V014_Q3_LOCAL_FEATURES + len(V015_C3_ACTION_BLOCKS)
V015_C3_GLOBAL_FEATURES = V014_Q3_GLOBAL_FEATURES
V015_C3_CURRENT_BEAM_START = V014_Q3_LOCAL_FEATURES * NUM_ACTIONS
V015_C3_CURRENT_SATELLITE_START = V015_C3_CURRENT_BEAM_START + NUM_ACTIONS
V015_C3_GLOBAL_START = V015_C3_LOCAL_FEATURES * NUM_ACTIONS


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V015_C3_STATE_SCHEMA,
        "schema_version": V015_C3_STATE_SCHEMA_VERSION,
        "source_schema": V014_Q3_STATE_SCHEMA,
        "source_schema_sha256": V014_Q3_STATE_SCHEMA_SHA256,
        "action_dim": NUM_ACTIONS,
        "source_state_dim": V014_Q3_STATE_DIM,
        "state_dim": V015_C3_STATE_DIM,
        "action_blocks": list(V015_C3_ACTION_BLOCKS),
        "normalization": {
            "current_same_beam_user_fraction": "other-users-counted-once-divide-by-max-users-minus-one",
            "current_same_satellite_user_fraction": "other-users-counted-once-divide-by-max-users-minus-one",
        },
        "physical_identity": "exact-norad-id-and-cell-id-for-beam; exact-norad-id-for-satellite",
        "time_semantics": "current-predecision-candidate-tables",
        "focal_exclusion": "exclude-row-user-and-count-each-other-user-at-most-once",
        "legal_actions_only": True,
        "forbidden_inputs": [
            "current-selected-actions",
            "outcomes",
            "q-values-or-ranks",
            "targets-or-signs",
            "evaluator",
            "rng",
        ],
    }


V015_C3_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV015C3StateError(MCRLContractError):
    """The V0.15 current-global C3 state is malformed or stale."""


EEAxisV015C3StateContractError = EEAxisV015C3StateError


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V015_C3_STATE_SCHEMA_SHA256,
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
class EEAxisV015C3StateObservation:
    """Immutable V0.15 state and common legal action mask."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V015_C3_STATE_SCHEMA:
            raise EEAxisV015C3StateError("unsupported V0.15 C3 state schema")
        if self.schema_sha256 != V015_C3_STATE_SCHEMA_SHA256:
            raise EEAxisV015C3StateError("V0.15 C3 state schema digest drifted")
        values = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if values.ndim != 2 or values.shape[1] != V015_C3_STATE_DIM:
            raise EEAxisV015C3StateError(
                f"state_matrix must have shape (U,{V015_C3_STATE_DIM})"
            )
        if masks.dtype != np.bool_ or masks.shape != (values.shape[0], NUM_ACTIONS):
            raise EEAxisV015C3StateError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(values)):
            raise EEAxisV015C3StateError("V0.15 C3 state must be finite")
        if values.flags.writeable or masks.flags.writeable:
            raise EEAxisV015C3StateError("V0.15 C3 state arrays must be immutable")
        current_blocks = values[:, V015_C3_CURRENT_BEAM_START:V015_C3_GLOBAL_START]
        if np.any(current_blocks < 0.0) or np.any(current_blocks > 1.0):
            raise EEAxisV015C3StateError("current-global fractions must lie in [0,1]")
        actual = _matrix_sha256(values, masks)
        if actual != self.state_sha256:
            raise EEAxisV015C3StateError(
                "V0.15 C3 state digest disagrees with its arrays"
            )
        return actual


def _positive(value: object, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise EEAxisV015C3StateError(
            f"{field} must be finite and positive"
        ) from error
    if not np.isfinite(parsed) or parsed <= 0.0:
        raise EEAxisV015C3StateError(f"{field} must be finite and positive")
    return parsed


def _anchor_tables(
    environment: StepEnvironment,
    observation: StepObservation,
) -> tuple[tuple[SlotTable, ...], np.ndarray]:
    if not isinstance(environment, StepEnvironment):
        raise EEAxisV015C3StateError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise EEAxisV015C3StateError("observation must be StepObservation")
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise EEAxisV015C3StateError(
            "observation is not the environment current predecision anchor"
        )
    users = int(observation.num_users)
    if users <= 0 or int(getattr(environment, "num_users", -1)) != users:
        raise EEAxisV015C3StateError("environment and observation user counts disagree")
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    if len(tables) != users or any(not isinstance(table, SlotTable) for table in tables):
        raise EEAxisV015C3StateError("anchor slot tables disagree with user count")
    masks = np.asarray(observation.masks)
    if masks.dtype != np.bool_ or masks.shape != (users, NUM_ACTIONS):
        raise EEAxisV015C3StateError(
            f"observation masks must be Boolean shape ({users},{NUM_ACTIONS})"
        )
    for uid, table in enumerate(tables):
        norads = np.asarray(table.norad_ids)
        cells = np.asarray(table.cell_ids)
        table_mask = np.asarray(table.mask)
        if (
            norads.shape != (NUM_ACTIONS,)
            or cells.shape != (NUM_ACTIONS,)
            or table_mask.dtype != np.bool_
            or table_mask.shape != (NUM_ACTIONS,)
            or not np.issubdtype(norads.dtype, np.integer)
            or not np.issubdtype(cells.dtype, np.integer)
            or np.any(table_mask & (norads < 0))
            or np.any(table_mask & (cells < 0))
        ):
            raise EEAxisV015C3StateError("anchor slot table is malformed")
        if not np.array_equal(masks[uid], table_mask):
            raise EEAxisV015C3StateError("observation masks disagree with slot tables")
    return tables, np.array(masks, dtype=np.bool_, copy=True, order="C")


def _legal_physical_keys(
    tables: tuple[SlotTable, ...], masks: np.ndarray
) -> tuple[frozenset[tuple[int, int]], ...]:
    result: list[frozenset[tuple[int, int]]] = []
    for uid, table in enumerate(tables):
        keys = {
            (int(table.norad_ids[action]), int(table.cell_ids[action]))
            for action in np.flatnonzero(masks[uid]).tolist()
        }
        result.append(frozenset(keys))
    return tuple(result)


def _current_global_blocks(
    tables: tuple[SlotTable, ...],
    masks: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    users = len(tables)
    denominator = float(max(users - 1, 1))
    legal_keys = _legal_physical_keys(tables, masks)
    beam = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    satellite = np.zeros_like(beam)
    for uid, table in enumerate(tables):
        for action in np.flatnonzero(masks[uid]).tolist():
            key = (int(table.norad_ids[action]), int(table.cell_ids[action]))
            beam_count = sum(
                key in legal_keys[other_uid]
                for other_uid in range(users)
                if other_uid != uid
            )
            satellite_count = sum(
                any(candidate_key[0] == key[0] for candidate_key in legal_keys[other_uid])
                for other_uid in range(users)
                if other_uid != uid
            )
            beam[uid, action] = np.float32(beam_count / denominator)
            satellite[uid, action] = np.float32(satellite_count / denominator)
    return beam, satellite


def extend_ee_axis_v014_q3_state(
    base_state: EEAxisV014Q3StateObservation,
    environment: StepEnvironment,
    observation: StepObservation,
) -> EEAxisV015C3StateObservation:
    """Append current-global blocks to an already encoded V0.14 state."""

    if not isinstance(base_state, EEAxisV014Q3StateObservation):
        raise EEAxisV015C3StateError("base_state must be an immutable V0.14 Q3 state")
    try:
        base_state.verify()
    except (TypeError, ValueError, MCRLContractError) as error:
        raise EEAxisV015C3StateError("base V0.14 Q3 state is invalid") from error
    tables, masks = _anchor_tables(environment, observation)
    users = len(tables)
    old = np.asarray(base_state.state_matrix)
    if old.shape != (users, V014_Q3_STATE_DIM):
        raise EEAxisV015C3StateError("base V0.14 Q3 state does not match user count")
    if not np.array_equal(base_state.action_masks, masks):
        raise EEAxisV015C3StateError("base V0.14 Q3 mask disagrees with current anchor")
    beam, satellite = _current_global_blocks(tables, masks)
    old_local_width = V014_Q3_LOCAL_FEATURES * NUM_ACTIONS
    old_global_start = V014_Q3_STATE_DIM - V014_Q3_GLOBAL_FEATURES
    values = np.concatenate(
        (
            old[:, :old_local_width],
            beam,
            satellite,
            old[:, old_global_start:],
        ),
        axis=1,
        dtype=np.float32,
    )
    if values.shape != (users, V015_C3_STATE_DIM):
        raise EEAxisV015C3StateError("V0.15 C3 state assembly has the wrong shape")
    values.setflags(write=False)
    masks.setflags(write=False)
    result = EEAxisV015C3StateObservation(
        schema=V015_C3_STATE_SCHEMA,
        schema_sha256=V015_C3_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    result.verify()
    return result


def encode_ee_axis_v015_c3_state(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    interval_s: float,
    kappa_bits: float,
) -> EEAxisV015C3StateObservation:
    """Encode V0.14 causal state plus current predecision spatial context."""

    interval = _positive(interval_s, field="interval_s")
    kappa = _positive(kappa_bits, field="kappa_bits")
    try:
        base = encode_ee_axis_v014_q3_state(
            environment,
            observation,
            interval_s=interval,
            kappa_bits=kappa,
        )
    except (TypeError, ValueError, MCRLContractError) as error:
        raise EEAxisV015C3StateError(
            f"V0.14 base state cannot be encoded: {error}"
        ) from error
    return extend_ee_axis_v014_q3_state(base, environment, observation)


encode_v015_c3_state = encode_ee_axis_v015_c3_state


__all__ = [
    "EEAxisV015C3StateContractError",
    "EEAxisV015C3StateError",
    "EEAxisV015C3StateObservation",
    "V015_C3_ACTION_BLOCKS",
    "V015_C3_CONTEXT_BLOCKS",
    "V015_C3_CURRENT_BEAM_START",
    "V015_C3_CURRENT_SATELLITE_START",
    "V015_C3_GLOBAL_START",
    "V015_C3_LOCAL_FEATURES",
    "V015_C3_GLOBAL_FEATURES",
    "V015_C3_STATE_DIM",
    "V015_C3_STATE_SCHEMA",
    "V015_C3_STATE_SCHEMA_SHA256",
    "encode_ee_axis_v015_c3_state",
    "encode_v015_c3_state",
    "extend_ee_axis_v014_q3_state",
]
