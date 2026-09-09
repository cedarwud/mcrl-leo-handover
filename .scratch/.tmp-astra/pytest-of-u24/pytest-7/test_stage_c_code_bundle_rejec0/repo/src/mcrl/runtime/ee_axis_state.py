"""Versioned causal state for Multi-Catfish MCRL V0.3.

The legacy MODQN observation remains the frozen 112-dimensional four-block
state.  V0.3 appends four action-slot-aligned, one-step-lagged physical
context blocks needed by the spatial-externality route:

* eligible served load;
* active-beam indicator;
* active-satellite indicator;
* maximum required link power.

It then appends four per-user causal features needed by the temporal route:

* previous recurrence power;
* current-to-segment-start transmit-gain ratio;
* segment age;
* a bit distinguishing no incumbent from an incumbent missing from the
  current candidate table.

All four blocks are derived from committed previous-slot state before the
current simultaneous action is chosen.  They are observations, not an action
coordination channel, and this module does not mutate the legacy environment.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

import numpy as np

from ..env.action_contract import Association, NUM_ACTIONS, SlotTable
from ..env.antenna import transmit_gain_linear
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .state_encoding import state_dim_for


EE_AXIS_STATE_SCHEMA = "multi-catfish-mcrl-v03-causal-state-v2"
EE_AXIS_BASE_STATE_DIM = state_dim_for(NUM_ACTIONS)
EE_AXIS_CONTEXT_BLOCKS = (
    "eligible_served_load",
    "beam_active",
    "satellite_active",
    "maximum_required_link_power",
)
EE_AXIS_C2_CONTEXT_FEATURES = (
    "previous_recurrence_power",
    "current_to_segment_start_gain_ratio",
    "segment_age",
    "missing_incumbent",
)
EE_AXIS_STATE_DIM = (
    EE_AXIS_BASE_STATE_DIM
    + len(EE_AXIS_CONTEXT_BLOCKS) * NUM_ACTIONS
    + len(EE_AXIS_C2_CONTEXT_FEATURES)
)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": EE_AXIS_STATE_SCHEMA,
        "base": "legacy-modqn-4C-v1",
        "base_state_dim": EE_AXIS_BASE_STATE_DIM,
        "action_dim": NUM_ACTIONS,
        "context_blocks": list(EE_AXIS_CONTEXT_BLOCKS),
        "temporal_context_features": list(EE_AXIS_C2_CONTEXT_FEATURES),
        "normalization": {
            "eligible_served_load": "divide-by-num-users",
            "beam_active": "binary",
            "satellite_active": "binary",
            "maximum_required_link_power": "divide-by-beam-power-max-w",
            "previous_recurrence_power": "divide-by-beam-power-max-w",
            "current_to_segment_start_gain_ratio": "current-gain-divide-by-start-gain",
            "segment_age": "divide-by-steps-per-episode",
            "missing_incumbent": "binary",
        },
        "time_semantics": "committed-previous-slot-predecision",
    }


EE_AXIS_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisStateContractError(MCRLContractError):
    """A proposed V0.3 state is not causal, aligned, or version-consistent."""


def _immutable(value: object, *, dtype: Any, field: str, ndim: int) -> np.ndarray:
    array = np.asarray(value)
    if array.ndim != ndim:
        raise EEAxisStateContractError(f"{field} must be {ndim}-dimensional")
    try:
        copied = np.array(array, dtype=dtype, copy=True, order="C")
    except (TypeError, ValueError) as error:
        raise EEAxisStateContractError(f"{field} has an invalid dtype") from error
    if np.issubdtype(copied.dtype, np.floating) and not np.all(np.isfinite(copied)):
        raise EEAxisStateContractError(f"{field} must be finite")
    copied.setflags(write=False)
    return copied


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": EE_AXIS_STATE_SCHEMA_SHA256,
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
class EEAxisStateObservation:
    """Immutable V0.3 state and action masks for one predecision anchor."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != EE_AXIS_STATE_SCHEMA:
            raise EEAxisStateContractError("unsupported V0.3 state schema")
        if self.schema_sha256 != EE_AXIS_STATE_SCHEMA_SHA256:
            raise EEAxisStateContractError("V0.3 state schema digest drifted")
        states = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if states.ndim != 2 or states.shape[1] != EE_AXIS_STATE_DIM:
            raise EEAxisStateContractError(
                f"state_matrix must have shape (U,{EE_AXIS_STATE_DIM})"
            )
        if masks.shape != (states.shape[0], NUM_ACTIONS) or masks.dtype != np.bool_:
            raise EEAxisStateContractError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(states)):
            raise EEAxisStateContractError("state_matrix must be finite")
        if states.flags.writeable or masks.flags.writeable:
            raise EEAxisStateContractError("V0.3 state arrays must be immutable")
        actual = _matrix_sha256(states, masks)
        if actual != self.state_sha256:
            raise EEAxisStateContractError("V0.3 state digest disagrees with arrays")
        return actual


def _current_slot_tables(
    environment: StepEnvironment, observation: StepObservation
) -> tuple[SlotTable, ...]:
    if not isinstance(environment, StepEnvironment):
        raise EEAxisStateContractError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise EEAxisStateContractError("observation must be StepObservation")
    current = getattr(environment, "_candidates", None)
    if current is None or current is not observation.candidates:
        raise EEAxisStateContractError(
            "observation is not the environment current predecision anchor"
        )
    tables = tuple(observation.candidates.slot_tables)
    if len(tables) != observation.num_users or any(
        not isinstance(table, SlotTable) for table in tables
    ):
        raise EEAxisStateContractError("anchor slot tables disagree with user count")
    return tables


def encode_ee_axis_state(
    environment: StepEnvironment,
    observation: StepObservation,
) -> EEAxisStateObservation:
    """Append the four causal C3 context blocks to the legacy state matrix."""

    tables = _current_slot_tables(environment, observation)
    users = observation.num_users
    if users <= 0 or int(getattr(environment, "num_users", -1)) != users:
        raise EEAxisStateContractError("environment and observation user counts disagree")
    base = _immutable(
        observation.state_matrix,
        dtype=np.float32,
        field="observation.state_matrix",
        ndim=2,
    )
    if base.shape != (users, EE_AXIS_BASE_STATE_DIM):
        raise EEAxisStateContractError(
            f"legacy base state must have shape ({users},{EE_AXIS_BASE_STATE_DIM})"
        )
    masks = _immutable(
        observation.masks,
        dtype=np.bool_,
        field="observation.masks",
        ndim=2,
    )
    if masks.shape != (users, NUM_ACTIONS):
        raise EEAxisStateContractError(
            f"observation masks must have shape ({users},{NUM_ACTIONS})"
        )
    if any(not np.array_equal(masks[index], table.mask) for index, table in enumerate(tables)):
        raise EEAxisStateContractError("observation masks disagree with slot tables")

    previous = tuple(getattr(environment, "_previous_association", ()))
    if len(previous) != users or any(
        association is not None and not isinstance(association, Association)
        for association in previous
    ):
        raise EEAxisStateContractError("previous served associations are malformed")
    eligible_load: dict[tuple[int, int], int] = {}
    for association in previous:
        if association is not None:
            key = (int(association.norad_id), int(association.cell_id))
            eligible_load[key] = eligible_load.get(key, 0) + 1

    radiating = getattr(environment, "_previous_radiating", None)
    if radiating is None:
        raise EEAxisStateContractError("environment lacks previous radiating state")
    norads = np.asarray(radiating.norad_ids)
    cells = np.asarray(radiating.cell_ids)
    powers = np.asarray(radiating.power_w, dtype=np.float64)
    if norads.shape != cells.shape or powers.shape != norads.shape:
        raise EEAxisStateContractError("previous radiating arrays disagree")
    if not np.all(np.isfinite(powers)) or np.any(powers < 0.0):
        raise EEAxisStateContractError("previous radiating power is malformed")
    active_power = {
        (int(norad), int(cell)): float(power)
        for norad, cell, power in zip(norads, cells, powers, strict=True)
    }
    if len(active_power) != len(norads):
        raise EEAxisStateContractError("previous radiating beam identities repeat")
    active_satellites = {key[0] for key in active_power}
    power_max = float(getattr(environment.physics, "beam_power_max_w", float("nan")))
    if not np.isfinite(power_max) or power_max <= 0.0:
        raise EEAxisStateContractError("beam power normalization is invalid")

    previous_link_power = np.asarray(
        getattr(environment, "_previous_link_power_w", None), dtype=np.float64
    )
    if previous_link_power.shape != (users,):
        raise EEAxisStateContractError("previous recurrence powers are malformed")
    if (
        not np.all(np.isfinite(previous_link_power))
        or np.any(previous_link_power < 0.0)
        or np.any(previous_link_power > power_max)
    ):
        raise EEAxisStateContractError("previous recurrence power is outside budget")
    segments = tuple(getattr(environment, "_segments", ()))
    if len(segments) != users:
        raise EEAxisStateContractError("previous power segments are malformed")
    steps_per_episode = int(
        getattr(getattr(environment.driver, "config", None), "steps_per_episode", 0)
    )
    if steps_per_episode <= 0:
        raise EEAxisStateContractError("segment-age normalization is invalid")

    load_block = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    beam_active_block = np.zeros_like(load_block)
    satellite_active_block = np.zeros_like(load_block)
    power_block = np.zeros_like(load_block)
    for uid, table in enumerate(tables):
        for action in np.flatnonzero(table.mask).tolist():
            key = (int(table.norad_ids[action]), int(table.cell_ids[action]))
            load_block[uid, action] = float(eligible_load.get(key, 0)) / float(users)
            beam_active_block[uid, action] = float(key in active_power)
            satellite_active_block[uid, action] = float(key[0] in active_satellites)
            power_block[uid, action] = float(active_power.get(key, 0.0)) / power_max

    temporal = np.zeros(
        (users, len(EE_AXIS_C2_CONTEXT_FEATURES)), dtype=np.float32
    )
    theta_start = 2 * NUM_ACTIONS
    theta_stop = 3 * NUM_ACTIONS
    theta_rad = np.asarray(base[:, theta_start:theta_stop], dtype=np.float64)
    for uid, (association, segment, table) in enumerate(
        zip(previous, segments, tables, strict=True)
    ):
        temporal[uid, 0] = float(previous_link_power[uid]) / power_max
        if association is None:
            if segment is not None or previous_link_power[uid] != 0.0:
                raise EEAxisStateContractError(
                    "unserved previous state retains a power segment"
                )
            continue
        if segment is None:
            raise EEAxisStateContractError("served incumbent lacks a power segment")
        if (
            int(getattr(segment, "norad_id", -1)) != association.norad_id
            or int(getattr(segment, "cell_id", -1)) != association.cell_id
        ):
            raise EEAxisStateContractError("incumbent and power segment disagree")
        start_gain = float(getattr(segment, "start_transmit_gain", float("nan")))
        age_steps = getattr(segment, "age_steps", None)
        if (
            not np.isfinite(start_gain)
            or start_gain <= 0.0
            or type(age_steps) is not int
            or age_steps < 0
        ):
            raise EEAxisStateContractError("incumbent power segment is malformed")
        temporal[uid, 2] = float(age_steps) / float(steps_per_episode)
        matches = np.flatnonzero(
            (table.norad_ids == association.norad_id)
            & (table.cell_ids == association.cell_id)
            & table.mask
        )
        if matches.size == 0:
            temporal[uid, 3] = 1.0
            continue
        if matches.size != 1:
            raise EEAxisStateContractError(
                "incumbent physical identity repeats in the candidate table"
            )
        action = int(matches[0])
        current_gain = float(
            transmit_gain_linear(
                np.asarray([np.degrees(theta_rad[uid, action])], dtype=np.float64)
            )[0]
        )
        if not np.isfinite(current_gain) or current_gain < 0.0:
            raise EEAxisStateContractError("current incumbent gain is malformed")
        temporal[uid, 1] = current_gain / start_gain

    values = np.concatenate(
        (
            base,
            load_block,
            beam_active_block,
            satellite_active_block,
            power_block,
            temporal,
        ),
        axis=1,
        dtype=np.float32,
    )
    values.setflags(write=False)
    state = EEAxisStateObservation(
        schema=EE_AXIS_STATE_SCHEMA,
        schema_sha256=EE_AXIS_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    state.verify()
    return state


__all__ = [
    "EE_AXIS_BASE_STATE_DIM",
    "EE_AXIS_CONTEXT_BLOCKS",
    "EE_AXIS_C2_CONTEXT_FEATURES",
    "EE_AXIS_STATE_DIM",
    "EE_AXIS_STATE_SCHEMA",
    "EE_AXIS_STATE_SCHEMA_SHA256",
    "EEAxisStateContractError",
    "EEAxisStateObservation",
    "encode_ee_axis_state",
]
