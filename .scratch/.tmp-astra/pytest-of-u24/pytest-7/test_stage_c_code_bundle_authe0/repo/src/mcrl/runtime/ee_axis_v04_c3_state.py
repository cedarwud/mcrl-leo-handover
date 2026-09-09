"""Causal V0.4 C3 victim-burden state.

V0.3's :mod:`ee_axis_state` is a sealed encoder.  This module deliberately
keeps that encoder intact and changes only the two C3-specific context blocks:
the eligible-user count becomes a previous-rate beam burden, and the binary
satellite-active flag becomes a previous-rate satellite burden.

The burden is computed from the committed previous slot only.  In particular,
this module never calls ``evaluate_actions`` and never inspects a current
joint action or an outcome.  The environment owns persistence of
``_previous_served_rate_bps``; this module owns aggregation, focal-user
exclusion, normalization, masking, and the V0.4 observation digest.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import Association, NUM_ACTIONS, SlotTable
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_state import (
    EE_AXIS_BASE_STATE_DIM,
    EE_AXIS_C2_CONTEXT_FEATURES,
    EE_AXIS_STATE_DIM as EE_AXIS_V03_STATE_DIM,
    encode_ee_axis_state,
)


EE_AXIS_V04_C3_STATE_SCHEMA = "multi-catfish-mcrl-v04-c3-victim-burden-state-v1"
EE_AXIS_V04_C3_STATE_DIM = EE_AXIS_V03_STATE_DIM
EE_AXIS_V04_C3_CONTEXT_BLOCKS = (
    "previous_beam_rate_burden",
    "beam_active",
    "previous_satellite_rate_burden",
    "maximum_required_link_power",
)
EE_AXIS_V04_C3_STATE_SCHEMA_VERSION = 1


def _schema_payload() -> dict[str, object]:
    return {
        "schema": EE_AXIS_V04_C3_STATE_SCHEMA,
        "schema_version": EE_AXIS_V04_C3_STATE_SCHEMA_VERSION,
        "base": "legacy-modqn-4C-v1",
        "base_state_dim": EE_AXIS_BASE_STATE_DIM,
        "action_dim": NUM_ACTIONS,
        "context_blocks": list(EE_AXIS_V04_C3_CONTEXT_BLOCKS),
        "temporal_context_features": list(EE_AXIS_C2_CONTEXT_FEATURES),
        "normalization": {
            "previous_beam_rate_burden": "interval-s-times-rate-divide-by-kappa-bits",
            "previous_satellite_rate_burden": "interval-s-times-rate-divide-by-kappa-bits",
            "beam_active": "binary",
            "maximum_required_link_power": "divide-by-beam-power-max-w",
            "previous_recurrence_power": "divide-by-beam-power-max-w",
            "current_to_segment_start_gain_ratio": "current-gain-divide-by-start-gain",
            "segment_age": "divide-by-steps-per-episode",
            "missing_incumbent": "binary",
        },
        "time_semantics": "committed-previous-slot-predecision",
        "burden_semantics": "exclude-focal-user-and-aggregate-by-physical-key",
    }


EE_AXIS_V04_C3_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV04C3StateContractError(MCRLContractError):
    """A proposed V0.4 observation violates the causal state contract."""


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
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
class EEAxisV04C3StateObservation:
    """Immutable V0.4 state and action masks for one predecision anchor."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != EE_AXIS_V04_C3_STATE_SCHEMA:
            raise EEAxisV04C3StateContractError("unsupported V0.4 C3 state schema")
        if self.schema_sha256 != EE_AXIS_V04_C3_STATE_SCHEMA_SHA256:
            raise EEAxisV04C3StateContractError("V0.4 C3 state schema digest drifted")
        states = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if states.ndim != 2 or states.shape[1] != EE_AXIS_V04_C3_STATE_DIM:
            raise EEAxisV04C3StateContractError(
                f"state_matrix must have shape (U,{EE_AXIS_V04_C3_STATE_DIM})"
            )
        if masks.shape != (states.shape[0], NUM_ACTIONS) or masks.dtype != np.bool_:
            raise EEAxisV04C3StateContractError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(states)):
            raise EEAxisV04C3StateContractError("state_matrix must be finite")
        if states.flags.writeable or masks.flags.writeable:
            raise EEAxisV04C3StateContractError("V0.4 C3 state arrays must be immutable")
        actual = _matrix_sha256(states, masks)
        if actual != self.state_sha256:
            raise EEAxisV04C3StateContractError("V0.4 C3 state digest disagrees with arrays")
        return actual


def _positive_finite(value: object, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise EEAxisV04C3StateContractError(f"{field} must be finite and positive") from error
    if not np.isfinite(parsed) or parsed <= 0.0:
        raise EEAxisV04C3StateContractError(f"{field} must be finite and positive")
    return parsed


def _previous_rates(environment: StepEnvironment, users: int) -> np.ndarray:
    if not isinstance(environment, StepEnvironment):
        raise EEAxisV04C3StateContractError("environment must be StepEnvironment")
    raw = getattr(environment, "_previous_served_rate_bps", None)
    if raw is None:
        raise EEAxisV04C3StateContractError(
            "environment lacks committed previous served-rate state"
        )
    try:
        rates = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise EEAxisV04C3StateContractError(
            "previous served rates are malformed"
        ) from error
    if rates.shape != (users,):
        raise EEAxisV04C3StateContractError("previous served rates are malformed")
    if not np.all(np.isfinite(rates)) or np.any(rates < 0.0):
        raise EEAxisV04C3StateContractError("previous served rates are malformed")
    return rates


def _previous_associations(
    environment: StepEnvironment, users: int
) -> tuple[Association | None, ...]:
    previous = tuple(getattr(environment, "_previous_association", ()))
    if len(previous) != users or any(
        association is not None and not isinstance(association, Association)
        for association in previous
    ):
        raise EEAxisV04C3StateContractError("previous associations are malformed")
    return previous


def _current_slot_tables(
    environment: StepEnvironment, observation: StepObservation
) -> tuple[SlotTable, ...]:
    if not isinstance(observation, StepObservation):
        raise EEAxisV04C3StateContractError("observation must be StepObservation")
    current = getattr(environment, "_candidates", None)
    if current is None or current is not observation.candidates:
        raise EEAxisV04C3StateContractError(
            "observation is not the environment current predecision anchor"
        )
    tables = tuple(observation.candidates.slot_tables)
    if len(tables) != observation.num_users or any(
        not isinstance(table, SlotTable) for table in tables
    ):
        raise EEAxisV04C3StateContractError("anchor slot tables disagree with user count")
    return tables


def _rate_burdens(
    tables: tuple[SlotTable, ...],
    previous: tuple[Association | None, ...],
    rates: np.ndarray,
    masks: np.ndarray,
    *,
    interval_s: float,
    kappa_bits: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate the committed previous rates onto current legal actions."""

    users = len(tables)
    scale = interval_s / kappa_bits
    beam_rate: dict[tuple[int, int], float] = {}
    satellite_rate: dict[int, float] = {}
    for uid, association in enumerate(previous):
        if association is None:
            # The environment's commit seam represents unserved users this
            # way, so an unserved rate cannot accidentally enter a burden.
            continue
        rate = float(rates[uid])
        key = (int(association.norad_id), int(association.cell_id))
        beam_rate[key] = beam_rate.get(key, 0.0) + rate
        satellite_rate[key[0]] = satellite_rate.get(key[0], 0.0) + rate

    beam = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    satellite = np.zeros_like(beam)
    for uid, table in enumerate(tables):
        for action in np.flatnonzero(masks[uid]).tolist():
            key = (int(table.norad_ids[action]), int(table.cell_ids[action]))
            # Exclude the focal user's own committed rate exactly, even if
            # its incumbent happens to be the action being represented.
            focal = previous[uid]
            own_rate = float(rates[uid]) if focal is not None else 0.0
            beam[uid, action] = (beam_rate.get(key, 0.0) - (
                own_rate if focal is not None and key == (focal.norad_id, focal.cell_id) else 0.0
            )) * scale
            satellite[uid, action] = (satellite_rate.get(key[0], 0.0) - (
                own_rate if focal is not None and key[0] == focal.norad_id else 0.0
            )) * scale
    # The source values are non-negative by construction.  A malformed
    # negative result would otherwise be silently converted by float32.
    if np.any(beam < 0.0) or np.any(satellite < 0.0):
        raise EEAxisV04C3StateContractError("computed victim burdens are negative")
    return beam, satellite


def encode_ee_axis_v04_c3_state(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    interval_s: float,
    kappa_bits: float,
) -> EEAxisV04C3StateObservation:
    """Encode one causal, action-aligned V0.4 C3 state.

    ``interval_s`` and ``kappa_bits`` are explicit frozen run constants.  The
    returned feature blocks are ``interval_s / kappa_bits`` times the sum of
    committed previous served rates, grouped by beam and satellite and with
    the focal user's own rate removed.
    """

    interval = _positive_finite(interval_s, field="interval_s")
    kappa = _positive_finite(kappa_bits, field="kappa_bits")
    tables = _current_slot_tables(environment, observation)
    users = observation.num_users
    if users <= 0 or int(getattr(environment, "num_users", -1)) != users:
        raise EEAxisV04C3StateContractError("environment and observation user counts disagree")

    # Calling the sealed V0.3 encoder gives us the frozen 112-D base, masks,
    # beam-activity/power blocks, and temporal features without duplicating
    # their semantics.  Only the two C3 context slices are replaced below.
    legacy = encode_ee_axis_state(environment, observation)
    values = np.array(legacy.state_matrix, dtype=np.float32, copy=True, order="C")
    masks = np.array(legacy.action_masks, dtype=np.bool_, copy=True, order="C")
    rates = _previous_rates(environment, users)
    previous = _previous_associations(environment, users)
    beam, satellite = _rate_burdens(
        tables,
        previous,
        rates,
        masks,
        interval_s=interval,
        kappa_bits=kappa,
    )

    beam_start = EE_AXIS_BASE_STATE_DIM
    satellite_start = beam_start + 2 * NUM_ACTIONS
    values[:, beam_start : beam_start + NUM_ACTIONS] = beam
    values[:, satellite_start : satellite_start + NUM_ACTIONS] = satellite

    values.setflags(write=False)
    masks.setflags(write=False)
    state = EEAxisV04C3StateObservation(
        schema=EE_AXIS_V04_C3_STATE_SCHEMA,
        schema_sha256=EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    state.verify()
    return state


__all__ = [
    "EE_AXIS_V04_C3_CONTEXT_BLOCKS",
    "EE_AXIS_V04_C3_STATE_DIM",
    "EE_AXIS_V04_C3_STATE_SCHEMA",
    "EE_AXIS_V04_C3_STATE_SCHEMA_SHA256",
    "EEAxisV04C3StateObservation",
    "EEAxisV04C3StateContractError",
    "encode_ee_axis_v04_c3_state",
]
