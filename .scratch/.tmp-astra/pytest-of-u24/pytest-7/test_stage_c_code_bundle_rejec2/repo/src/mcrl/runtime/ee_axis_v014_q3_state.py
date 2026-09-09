"""Deployable V0.14 state for the ZR C3 learner.

The V0.13 oracle teacher is deliberately unavailable at deployment: its
``b0`` joint reference, counterfactual rates, compatibility bit ``g``, and
selected actions are outcomes of other computations and may not enter Q3.
This encoder therefore extends the causal V0.4 view only with committed
previous-slot information that helps distinguish a focal user leaving its
incumbent beam from merely choosing among unrelated candidates.

Layout::

    [10 action-aligned blocks * 28 actions, 7 global features]

The first eight action blocks and first four globals are byte-for-byte the
V0.4 C3 view.  The new action blocks are (i) physical continuation of the
committed incumbent and (ii) committed served load on the candidate beam
with the focal user excluded.  The new globals describe the incumbent beam's
non-focal rate burden, non-focal load, and whether the focal user supplied
the committed maximum link power on that beam.

No evaluator, Q function, target, current outcome, future value, or RNG is
queried here.  The returned arrays are immutable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import Association, NUM_ACTIONS, SlotTable
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_state import EE_AXIS_C2_CONTEXT_FEATURES
from .ee_axis_v04_c3_state import (
    EE_AXIS_V04_C3_CONTEXT_BLOCKS,
    EE_AXIS_V04_C3_STATE_DIM,
    EE_AXIS_V04_C3_STATE_SCHEMA,
    EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
    encode_ee_axis_v04_c3_state,
)


V014_Q3_LOCAL_FEATURES = 10
V014_Q3_GLOBAL_FEATURES = 7
V014_Q3_STATE_DIM = V014_Q3_LOCAL_FEATURES * NUM_ACTIONS + V014_Q3_GLOBAL_FEATURES
V014_Q3_STATE_SCHEMA = "multi-catfish-mcrl-v014-zr-q3-state-v1"
V014_Q3_STATE_SCHEMA_VERSION = 1
V014_Q3_ACTION_BLOCKS = (
    "access",
    "log1p_candidate_sinr",
    "theta_rad",
    "ungated_demand_load",
    *EE_AXIS_V04_C3_CONTEXT_BLOCKS,
    "continues_committed_incumbent",
    "committed_beam_load_excluding_focal",
)
V014_Q3_GLOBAL_FEATURE_NAMES = (
    *EE_AXIS_C2_CONTEXT_FEATURES,
    "incumbent_beam_rate_burden_excluding_focal",
    "incumbent_beam_load_excluding_focal",
    "focal_is_incumbent_beam_power_leader",
)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V014_Q3_STATE_SCHEMA,
        "schema_version": V014_Q3_STATE_SCHEMA_VERSION,
        "source_schema": EE_AXIS_V04_C3_STATE_SCHEMA,
        "source_schema_sha256": EE_AXIS_V04_C3_STATE_SCHEMA_SHA256,
        "action_dim": NUM_ACTIONS,
        "state_dim": V014_Q3_STATE_DIM,
        "action_blocks": list(V014_Q3_ACTION_BLOCKS),
        "global_features": list(V014_Q3_GLOBAL_FEATURE_NAMES),
        "normalization": {
            "committed_beam_load_excluding_focal": "divide-by-num-users",
            "incumbent_beam_rate_burden_excluding_focal": (
                "interval-s-times-committed-served-rate-divide-by-kappa-bits"
            ),
            "incumbent_beam_load_excluding_focal": "divide-by-num-users",
            "focal_is_incumbent_beam_power_leader": "binary-exact-max-power",
        },
        "time_semantics": "current-predecision-plus-committed-previous-slot",
        "focal_exclusion": "exclude-the-row-user-from-every-added-burden",
        "forbidden_inputs": [
            "b0",
            "q1-or-o2-values-ranks-or-actions",
            "counterfactual-rates-powers-or-signatures",
            "compatibility-g",
            "current-selected-actions-or-outcomes",
            "future-information",
            "target-values-or-signs",
        ],
    }


V014_Q3_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV014Q3StateError(MCRLContractError):
    """The deployable ZR-Q3 state is stale, leaky, or malformed."""


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V014_Q3_STATE_SCHEMA_SHA256,
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
class EEAxisV014Q3StateObservation:
    """Immutable action-aligned ZR-Q3 observation and common safe mask."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V014_Q3_STATE_SCHEMA:
            raise EEAxisV014Q3StateError("unsupported V0.14 Q3 state schema")
        if self.schema_sha256 != V014_Q3_STATE_SCHEMA_SHA256:
            raise EEAxisV014Q3StateError("V0.14 Q3 state schema digest drifted")
        values = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if values.ndim != 2 or values.shape[1] != V014_Q3_STATE_DIM:
            raise EEAxisV014Q3StateError(
                f"state_matrix must have shape (U,{V014_Q3_STATE_DIM})"
            )
        if masks.dtype != np.bool_ or masks.shape != (values.shape[0], NUM_ACTIONS):
            raise EEAxisV014Q3StateError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(values)):
            raise EEAxisV014Q3StateError("V0.14 Q3 state must be finite")
        if values.flags.writeable or masks.flags.writeable:
            raise EEAxisV014Q3StateError("V0.14 Q3 state arrays must be immutable")
        actual = _matrix_sha256(values, masks)
        if actual != self.state_sha256:
            raise EEAxisV014Q3StateError(
                "V0.14 Q3 state digest disagrees with its arrays"
            )
        return actual


def _positive(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise EEAxisV014Q3StateError(
            f"{field} must be finite and positive"
        ) from error
    if not np.isfinite(result) or result <= 0.0:
        raise EEAxisV014Q3StateError(f"{field} must be finite and positive")
    return result


def _committed_inputs(
    environment: StepEnvironment,
    observation: StepObservation,
) -> tuple[
    tuple[SlotTable, ...],
    tuple[Association | None, ...],
    np.ndarray,
    np.ndarray,
    dict[tuple[int, int], float],
]:
    if not isinstance(environment, StepEnvironment) or not isinstance(
        observation, StepObservation
    ):
        raise EEAxisV014Q3StateError(
            "environment and observation must be canonical step objects"
        )
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise EEAxisV014Q3StateError("observation is not the current predecision anchor")
    users = int(observation.num_users)
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    if len(tables) != users or any(not isinstance(table, SlotTable) for table in tables):
        raise EEAxisV014Q3StateError("current candidate tables are malformed")
    previous = tuple(getattr(environment, "_previous_association", ()))
    if len(previous) != users or any(
        item is not None and not isinstance(item, Association) for item in previous
    ):
        raise EEAxisV014Q3StateError("committed associations are malformed")
    rates = np.asarray(
        getattr(environment, "_previous_served_rate_bps", None), dtype=np.float64
    )
    powers = np.asarray(
        getattr(environment, "_previous_link_power_w", None), dtype=np.float64
    )
    if (
        rates.shape != (users,)
        or powers.shape != (users,)
        or not np.all(np.isfinite(rates))
        or not np.all(np.isfinite(powers))
        or np.any(rates < 0.0)
        or np.any(powers < 0.0)
    ):
        raise EEAxisV014Q3StateError(
            "committed served rates and link powers must be finite nonnegative user vectors"
        )
    for uid, association in enumerate(previous):
        if association is None and (rates[uid] != 0.0 or powers[uid] != 0.0):
            raise EEAxisV014Q3StateError(
                "an unserved committed user retains rate or link power"
            )
    radiating = getattr(environment, "_previous_radiating", None)
    norads = np.asarray(getattr(radiating, "norad_ids", None))
    cells = np.asarray(getattr(radiating, "cell_ids", None))
    beam_power = np.asarray(getattr(radiating, "power_w", None), dtype=np.float64)
    if (
        norads.ndim != 1
        or cells.shape != norads.shape
        or beam_power.shape != norads.shape
        or not np.issubdtype(norads.dtype, np.integer)
        or not np.issubdtype(cells.dtype, np.integer)
        or not np.all(np.isfinite(beam_power))
        or np.any(beam_power < 0.0)
    ):
        raise EEAxisV014Q3StateError("committed radiating-beam state is malformed")
    beam_max = {
        (int(norad), int(cell)): float(power)
        for norad, cell, power in zip(norads, cells, beam_power, strict=True)
    }
    if len(beam_max) != len(norads):
        raise EEAxisV014Q3StateError("committed radiating beam identities repeat")
    for uid, association in enumerate(previous):
        if association is None:
            continue
        key = (int(association.norad_id), int(association.cell_id))
        if key not in beam_max or powers[uid] > beam_max[key]:
            raise EEAxisV014Q3StateError(
                "committed user link power disagrees with its radiating beam"
            )
    return tables, previous, rates, powers, beam_max


def encode_ee_axis_v014_q3_state(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    interval_s: float,
    kappa_bits: float,
) -> EEAxisV014Q3StateObservation:
    """Extend the V0.4 C3 view using only deployable predecision state."""

    interval = _positive(interval_s, field="interval_s")
    kappa = _positive(kappa_bits, field="kappa_bits")
    legacy = encode_ee_axis_v04_c3_state(
        environment,
        observation,
        interval_s=interval,
        kappa_bits=kappa,
    )
    tables, previous, rates, powers, beam_max = _committed_inputs(
        environment, observation
    )
    users = int(observation.num_users)
    masks = np.array(legacy.action_masks, dtype=np.bool_, copy=True, order="C")
    old = np.asarray(legacy.state_matrix, dtype=np.float32)
    old_local_width = EE_AXIS_V04_C3_STATE_DIM - len(EE_AXIS_C2_CONTEXT_FEATURES)
    if old_local_width != 8 * NUM_ACTIONS:
        raise EEAxisV014Q3StateError("V0.4 action/global layout drifted")

    continuation = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    nonfocal_load = np.zeros_like(continuation)
    incumbent_rate_burden = np.zeros((users, 1), dtype=np.float32)
    incumbent_load = np.zeros((users, 1), dtype=np.float32)
    incumbent_power_leader = np.zeros((users, 1), dtype=np.float32)

    committed_keys = [
        None
        if association is None
        else (int(association.norad_id), int(association.cell_id))
        for association in previous
    ]
    for uid, table in enumerate(tables):
        own_key = committed_keys[uid]
        for action_raw in np.flatnonzero(masks[uid]).tolist():
            action = int(action_raw)
            key = (int(table.norad_ids[action]), int(table.cell_ids[action]))
            continuation[uid, action] = float(own_key == key)
            count = sum(
                1
                for other_uid, other_key in enumerate(committed_keys)
                if other_uid != uid and other_key == key
            )
            nonfocal_load[uid, action] = float(count) / float(users)
        if own_key is None:
            continue
        victims = [
            other_uid
            for other_uid, other_key in enumerate(committed_keys)
            if other_uid != uid and other_key == own_key
        ]
        incumbent_rate_burden[uid, 0] = np.float32(
            interval * float(np.sum(rates[victims], dtype=np.float64)) / kappa
        )
        incumbent_load[uid, 0] = np.float32(float(len(victims)) / float(users))
        incumbent_power_leader[uid, 0] = float(
            powers[uid] > 0.0 and powers[uid] == beam_max[own_key]
        )

    values = np.concatenate(
        (
            old[:, :old_local_width],
            continuation,
            nonfocal_load,
            old[:, old_local_width:],
            incumbent_rate_burden,
            incumbent_load,
            incumbent_power_leader,
        ),
        axis=1,
        dtype=np.float32,
    )
    if values.shape != (users, V014_Q3_STATE_DIM):
        raise EEAxisV014Q3StateError("V0.14 Q3 state assembly has the wrong shape")
    values.setflags(write=False)
    masks.setflags(write=False)
    result = EEAxisV014Q3StateObservation(
        schema=V014_Q3_STATE_SCHEMA,
        schema_sha256=V014_Q3_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    result.verify()
    return result


__all__ = [
    "EEAxisV014Q3StateError",
    "EEAxisV014Q3StateObservation",
    "V014_Q3_ACTION_BLOCKS",
    "V014_Q3_GLOBAL_FEATURE_NAMES",
    "V014_Q3_GLOBAL_FEATURES",
    "V014_Q3_LOCAL_FEATURES",
    "V014_Q3_STATE_DIM",
    "V014_Q3_STATE_SCHEMA",
    "V014_Q3_STATE_SCHEMA_SHA256",
    "encode_ee_axis_v014_q3_state",
]
