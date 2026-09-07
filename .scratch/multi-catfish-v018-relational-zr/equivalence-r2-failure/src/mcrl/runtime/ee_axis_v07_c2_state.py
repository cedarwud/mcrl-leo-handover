"""Q2-specific signed-motion state for Multi-Catfish MCRL V0.7 C2.

The sealed V0.3 encoder does not expose a candidate's signed range rate.  That
omission is harmless for an instantaneous scorer but aliases approaching and
receding candidates for a feed-forward learner whose P0/B1/B2 labels describe
future slots.

This encoder keeps the state at 228 dimensions without deleting the 112-D base
or any independent context.  It replaces only ``beam_active``: in the
canonical environment a beam radiates iff it served at least one user, so that
bit is exactly ``eligible_served_load > 0``.  The equality is checked before
the slice is reused; a malformed or non-canonical state fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import (
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    SlotAssignment,
)
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_state import (
    EE_AXIS_BASE_STATE_DIM,
    EE_AXIS_C2_CONTEXT_FEATURES,
    EE_AXIS_STATE_DIM,
    EE_AXIS_STATE_SCHEMA,
    EE_AXIS_STATE_SCHEMA_SHA256,
    encode_ee_axis_state,
)


V07_C2_Q2_STATE_SCHEMA = (
    "multi-catfish-mcrl-v07-c2-q2-signed-range-rate-state-v1"
)
V07_C2_Q2_STATE_SCHEMA_VERSION = 1
V07_C2_Q2_STATE_DIM = EE_AXIS_STATE_DIM
V07_C2_Q2_CONTEXT_BLOCKS = (
    "eligible_served_load",
    "signed_range_rate_km_s",
    "satellite_active",
    "maximum_required_link_power",
)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V07_C2_Q2_STATE_SCHEMA,
        "schema_version": V07_C2_Q2_STATE_SCHEMA_VERSION,
        "source_schema": EE_AXIS_STATE_SCHEMA,
        "source_schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
        "base_state_dim": EE_AXIS_BASE_STATE_DIM,
        "state_dim": V07_C2_Q2_STATE_DIM,
        "action_dim": NUM_ACTIONS,
        "context_blocks": list(V07_C2_Q2_CONTEXT_BLOCKS),
        "temporal_context_features": list(EE_AXIS_C2_CONTEXT_FEATURES),
        "replaced_context_block": "beam_active",
        "redundancy_identity": "beam_active == (eligible_served_load > 0)",
        "normalization": {
            "signed_range_rate_km_s": "raw-km-per-s-negative-approaching",
        },
        "alignment": "repeat-satellite-rate-over-seven-legal-action-slots",
        "illegal_action_fill": 0.0,
        "base_access_block": "preserved-byte-for-byte",
        "time_semantics": "current-predecision-d2-measurement",
    }


V07_C2_Q2_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV07C2StateContractError(MCRLContractError):
    """The signed-motion Q2 observation is malformed or not canonical."""


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V07_C2_Q2_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in values.ravel()],
        "masks": masks.astype(np.uint8).tolist(),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EEAxisV07C2StateObservation:
    """Immutable V0.7 Q2 state and native masks for one predecision anchor."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V07_C2_Q2_STATE_SCHEMA:
            raise EEAxisV07C2StateContractError("unsupported V0.7 C2 Q2 state schema")
        if self.schema_sha256 != V07_C2_Q2_STATE_SCHEMA_SHA256:
            raise EEAxisV07C2StateContractError("V0.7 C2 Q2 state schema digest drifted")
        states = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if states.ndim != 2 or states.shape[1] != V07_C2_Q2_STATE_DIM:
            raise EEAxisV07C2StateContractError(
                f"state_matrix must have shape (U,{V07_C2_Q2_STATE_DIM})"
            )
        if masks.shape != (states.shape[0], NUM_ACTIONS) or masks.dtype != np.bool_:
            raise EEAxisV07C2StateContractError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(states)):
            raise EEAxisV07C2StateContractError("state_matrix must be finite")
        if states.flags.writeable or masks.flags.writeable:
            raise EEAxisV07C2StateContractError("V0.7 C2 Q2 state arrays must be immutable")
        actual = _matrix_sha256(states, masks)
        if actual != self.state_sha256:
            raise EEAxisV07C2StateContractError(
                "V0.7 C2 Q2 state digest disagrees with arrays"
            )
        return actual


def _signed_range_rate_block(
    observation: StepObservation,
    masks: np.ndarray,
) -> np.ndarray:
    assignments = tuple(getattr(observation.candidates, "assignments", ()))
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    users = masks.shape[0]
    if len(assignments) != users or any(
        not isinstance(assignment, SlotAssignment) for assignment in assignments
    ):
        raise EEAxisV07C2StateContractError(
            "current candidates lack per-user SlotAssignment motion state"
        )
    if len(tables) != users:
        raise EEAxisV07C2StateContractError("current candidate tables are malformed")

    radial = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    for uid, (assignment, table) in enumerate(zip(assignments, tables, strict=True)):
        rates = np.asarray(assignment.radial_rate_km_s, dtype=np.float64)
        if rates.shape != (NUM_SATELLITE_SLOTS,) or not np.all(np.isfinite(rates)):
            raise EEAxisV07C2StateContractError("signed range rates must be finite")
        for slot in range(NUM_SATELLITE_SLOTS):
            start = slot * NUM_BEAM_SLOTS
            stop = start + NUM_BEAM_SLOTS
            slot_mask = masks[uid, start:stop]
            if not assignment.occupied[slot] and bool(np.any(slot_mask)):
                raise EEAxisV07C2StateContractError(
                    "an unoccupied satellite slot contains a legal action"
                )
            if bool(np.any(slot_mask)):
                expected_norad = int(assignment.norad_ids[slot])
                if expected_norad < 0 or np.any(
                    np.asarray(table.norad_ids[start:stop])[slot_mask]
                    != expected_norad
                ):
                    raise EEAxisV07C2StateContractError(
                        "slot assignment and physical action identities disagree"
                    )
                radial[uid, start:stop][slot_mask] = np.float32(rates[slot])
    return radial


def encode_ee_axis_v07_c2_state(
    environment: StepEnvironment,
    observation: StepObservation,
) -> EEAxisV07C2StateObservation:
    """Encode the 228-D Q2 state while preserving the sealed 112-D base."""

    legacy = encode_ee_axis_state(environment, observation)
    values = np.array(legacy.state_matrix, dtype=np.float32, copy=True, order="C")
    masks = np.array(legacy.action_masks, dtype=np.bool_, copy=True, order="C")

    load_start = EE_AXIS_BASE_STATE_DIM
    beam_active_start = load_start + NUM_ACTIONS
    load = values[:, load_start:beam_active_start]
    beam_active = values[
        :, beam_active_start : beam_active_start + NUM_ACTIONS
    ]
    recoverable_beam_active = (load > 0.0).astype(np.float32)
    if not np.array_equal(beam_active, recoverable_beam_active):
        raise EEAxisV07C2StateContractError(
            "beam_active is not redundant with eligible_served_load"
        )

    values[
        :, beam_active_start : beam_active_start + NUM_ACTIONS
    ] = _signed_range_rate_block(observation, masks)
    values.setflags(write=False)
    masks.setflags(write=False)
    state = EEAxisV07C2StateObservation(
        schema=V07_C2_Q2_STATE_SCHEMA,
        schema_sha256=V07_C2_Q2_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    state.verify()
    return state


__all__ = [
    "EEAxisV07C2StateContractError",
    "EEAxisV07C2StateObservation",
    "V07_C2_Q2_CONTEXT_BLOCKS",
    "V07_C2_Q2_STATE_DIM",
    "V07_C2_Q2_STATE_SCHEMA",
    "V07_C2_Q2_STATE_SCHEMA_SHA256",
    "V07_C2_Q2_STATE_SCHEMA_VERSION",
    "encode_ee_axis_v07_c2_state",
]
