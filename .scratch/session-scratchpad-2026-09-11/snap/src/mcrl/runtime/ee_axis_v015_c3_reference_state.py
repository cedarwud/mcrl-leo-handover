"""Pure V0.15 C3 reference-conditioned spatial state.

This module adds a small, predecision view of the *detached* joint reference
action to the sealed V0.14 Q3 state.  The reference action vector is supplied
by the caller; this encoder never computes a Q value, evaluates a branch, or
advances an environment.  All reference rows are materialised before any
focal row is encoded, so Q3 cannot feed back into the reference seam.

The state layout preserves the V0.14 action-local and global values, while
keeping the feature-major contract expected by the ActionSet scorer::

    [V0.14 action-local prefix (280),
     reference_same_beam_fraction (28),
     reference_same_satellite_fraction (28),
     reference_beam_power_gap (28),
     V0.14 globals (7)]

The first two blocks count only non-focal users whose reference action is
opening-service-feasible.  Physical ``(norad_id, cell_id)`` identities are
used for beam matches and ``norad_id`` for satellite matches; flat action
indices are never compared.  The power block is the capped current required
power of the focal candidate minus the largest capped current required power
of a feasible peer reference on the same physical beam.
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
    EEAxisV014Q3StateError,
    V014_Q3_GLOBAL_FEATURES,
    V014_Q3_LOCAL_FEATURES,
    V014_Q3_STATE_DIM,
    V014_Q3_STATE_SCHEMA,
    V014_Q3_STATE_SCHEMA_SHA256,
    encode_ee_axis_v014_q3_state,
)


V015_C3_REFERENCE_ACTION_BLOCKS = (
    "reference_same_beam_fraction",
    "reference_same_satellite_fraction",
    "reference_beam_power_gap",
)
V015_C3_REFERENCE_CONTEXT_BLOCKS = V015_C3_REFERENCE_ACTION_BLOCKS
V015_C3_REFERENCE_PREFIX_DIM = V014_Q3_STATE_DIM
V015_C3_REFERENCE_LOCAL_PREFIX_DIM = V014_Q3_LOCAL_FEATURES * NUM_ACTIONS
V015_C3_REFERENCE_LOCAL_FEATURES = 13
V015_C3_REFERENCE_GLOBAL_FEATURES = 7
V015_C3_REFERENCE_STATE_DIM = (
    V015_C3_REFERENCE_PREFIX_DIM + len(V015_C3_REFERENCE_ACTION_BLOCKS) * NUM_ACTIONS
)
V015_C3_REFERENCE_STATE_SCHEMA = (
    "multi-catfish-mcrl-v015-c3-reference-conditioned-state-v1"
)
V015_C3_REFERENCE_STATE_SCHEMA_VERSION = 1
V015_C3_REFERENCE_BEAM_START = V015_C3_REFERENCE_LOCAL_PREFIX_DIM
V015_C3_REFERENCE_SATELLITE_START = (
    V015_C3_REFERENCE_BEAM_START + NUM_ACTIONS
)
V015_C3_REFERENCE_POWER_GAP_START = (
    V015_C3_REFERENCE_SATELLITE_START + NUM_ACTIONS
)
V015_C3_REFERENCE_GLOBAL_START = (
    V015_C3_REFERENCE_POWER_GAP_START + NUM_ACTIONS
)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V015_C3_REFERENCE_STATE_SCHEMA,
        "schema_version": V015_C3_REFERENCE_STATE_SCHEMA_VERSION,
        "prefix_schema": V014_Q3_STATE_SCHEMA,
        "prefix_schema_sha256": V014_Q3_STATE_SCHEMA_SHA256,
        "prefix_state_dim": V015_C3_REFERENCE_PREFIX_DIM,
        "action_dim": NUM_ACTIONS,
        "local_feature_dim": V015_C3_REFERENCE_LOCAL_FEATURES,
        "global_feature_dim": V015_C3_REFERENCE_GLOBAL_FEATURES,
        "state_dim": V015_C3_REFERENCE_STATE_DIM,
        "layout": (
            "v014-action-local-prefix-then-three-reference-action-blocks-"
            "then-v014-globals"
        ),
        "action_blocks": list(V015_C3_REFERENCE_ACTION_BLOCKS),
        "normalization": {
            "reference_same_beam_fraction": (
                "feasible-nonfocal-reference-users-divide-by-max-users-minus-one"
            ),
            "reference_same_satellite_fraction": (
                "feasible-nonfocal-reference-users-divide-by-max-users-minus-one"
            ),
            "reference_beam_power_gap": (
                "min(current-required-power-divide-by-pmax,1)-peer-beam-maximum"
            ),
        },
        "physical_identity": (
            "exact-norad-id-and-cell-id-for-beam; exact-norad-id-for-satellite"
        ),
        "time_semantics": "current-predecision-reference-conditioned",
        "reference_semantics": (
            "all-reference-actions-materialized-before-each-focal-row"
        ),
        "focal_exclusion": "exclude-row-user",
        "empty_reference": "minus-one-only-when-native-mask-is-empty",
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


V015_C3_REFERENCE_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV015C3ReferenceStateError(MCRLContractError):
    """The V0.15 reference-conditioned state violates its contract."""


EEAxisV015C3ReferenceStateContractError = EEAxisV015C3ReferenceStateError


def _matrix_sha256(values: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V015_C3_REFERENCE_STATE_SCHEMA_SHA256,
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
class EEAxisV015C3ReferenceStateObservation:
    """Immutable V0.15 state and the native safe action mask."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V015_C3_REFERENCE_STATE_SCHEMA:
            raise EEAxisV015C3ReferenceStateError(
                "unsupported V0.15 reference C3 state schema"
            )
        if self.schema_sha256 != V015_C3_REFERENCE_STATE_SCHEMA_SHA256:
            raise EEAxisV015C3ReferenceStateError(
                "V0.15 reference C3 state schema digest drifted"
            )
        values = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if values.ndim != 2 or values.shape[1] != V015_C3_REFERENCE_STATE_DIM:
            raise EEAxisV015C3ReferenceStateError(
                "state_matrix must have shape "
                f"(U,{V015_C3_REFERENCE_STATE_DIM})"
            )
        if masks.dtype != np.bool_ or masks.shape != (values.shape[0], NUM_ACTIONS):
            raise EEAxisV015C3ReferenceStateError(
                f"action_masks must be Boolean shape (U,{NUM_ACTIONS})"
            )
        if not np.all(np.isfinite(values)):
            raise EEAxisV015C3ReferenceStateError(
                "V0.15 reference C3 state must be finite"
            )
        if values.flags.writeable or masks.flags.writeable:
            raise EEAxisV015C3ReferenceStateError(
                "V0.15 reference C3 state arrays must be immutable"
            )
        fractions = values[
            :,
            V015_C3_REFERENCE_BEAM_START : V015_C3_REFERENCE_POWER_GAP_START,
        ]
        if np.any(fractions < 0.0) or np.any(fractions > 1.0):
            raise EEAxisV015C3ReferenceStateError(
                "reference fractions must lie in [0,1]"
            )
        gaps = values[
            :,
            V015_C3_REFERENCE_POWER_GAP_START : V015_C3_REFERENCE_GLOBAL_START,
        ]
        if np.any(gaps < -1.0) or np.any(gaps > 1.0):
            raise EEAxisV015C3ReferenceStateError(
                "reference beam power gaps must lie in [-1,1]"
            )
        actual = _matrix_sha256(values, masks)
        if actual != self.state_sha256:
            raise EEAxisV015C3ReferenceStateError(
                "V0.15 reference C3 state digest disagrees with its arrays"
            )
        return actual


def _positive(value: object, *, field: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise EEAxisV015C3ReferenceStateError(
            f"{field} must be finite and positive"
        )
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise EEAxisV015C3ReferenceStateError(
            f"{field} must be finite and positive"
        ) from error
    if not np.isfinite(parsed) or parsed <= 0.0:
        raise EEAxisV015C3ReferenceStateError(
            f"{field} must be finite and positive"
        )
    return parsed


def _anchor(
    environment: StepEnvironment,
    observation: StepObservation,
) -> tuple[tuple[SlotTable, ...], np.ndarray]:
    if not isinstance(environment, StepEnvironment):
        raise EEAxisV015C3ReferenceStateError(
            "environment must be StepEnvironment"
        )
    if not isinstance(observation, StepObservation):
        raise EEAxisV015C3ReferenceStateError(
            "observation must be StepObservation"
        )
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise EEAxisV015C3ReferenceStateError(
            "observation is not the environment current predecision anchor"
        )
    users = int(observation.num_users)
    if users <= 0 or int(getattr(environment, "num_users", -1)) != users:
        raise EEAxisV015C3ReferenceStateError(
            "environment and observation user counts disagree"
        )
    tables = tuple(getattr(observation.candidates, "slot_tables", ()))
    native = np.asarray(observation.masks)
    if (
        len(tables) != users
        or any(not isinstance(table, SlotTable) for table in tables)
        or native.dtype != np.bool_
        or native.shape != (users, NUM_ACTIONS)
    ):
        raise EEAxisV015C3ReferenceStateError(
            f"anchor tables and native mask must have shape ({users},{NUM_ACTIONS})"
        )
    native_copy = np.array(native, dtype=np.bool_, copy=True, order="C")
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
            or not np.array_equal(native_copy[uid], table_mask)
        ):
            raise EEAxisV015C3ReferenceStateError(
                "observation native mask disagrees with slot tables"
            )
    return tables, native_copy


def _reference_vector(
    tables: tuple[SlotTable, ...],
    native: np.ndarray,
    reference_actions: object,
) -> np.ndarray:
    try:
        raw = np.asarray(reference_actions)
    except (TypeError, ValueError) as error:
        raise EEAxisV015C3ReferenceStateError(
            "reference_actions are malformed"
        ) from error
    users = len(tables)
    if (
        raw.shape != (users,)
        or raw.dtype.kind not in "iu"
        or raw.dtype.kind == "b"
    ):
        raise EEAxisV015C3ReferenceStateError(
            f"reference_actions must be an integer vector of shape ({users},)"
        )
    raw_values = raw.tolist()
    # Validate the Python integers before narrowing an unsigned input to
    # int64; otherwise uint64 values above int64's range could wrap to -1 and
    # accidentally pass the all-empty-row sentinel rule.
    for uid, value in enumerate(raw_values):
        action = int(value)
        if action == -1:
            if np.any(native[uid]):
                raise EEAxisV015C3ReferenceStateError(
                    f"reference_actions[{uid}] may be -1 only for an all-empty native row"
                )
            continue
        if not 0 <= action < NUM_ACTIONS or not bool(native[uid, action]):
            raise EEAxisV015C3ReferenceStateError(
                f"reference_actions[{uid}] is not legal under the native mask"
            )
    references = np.array(raw_values, dtype=np.int64, copy=True, order="C")
    references.setflags(write=False)
    return references


def _opening_mask(
    native: np.ndarray,
    opening_service_feasible: object,
) -> np.ndarray:
    try:
        raw = np.asarray(opening_service_feasible)
    except (TypeError, ValueError) as error:
        raise EEAxisV015C3ReferenceStateError(
            "opening_service_feasible is malformed"
        ) from error
    if raw.dtype != np.bool_ or raw.shape != native.shape:
        raise EEAxisV015C3ReferenceStateError(
            "opening_service_feasible must be Boolean with the native-mask shape"
        )
    opening = np.array(raw, dtype=np.bool_, copy=True, order="C")
    if np.any(opening & ~native):
        raise EEAxisV015C3ReferenceStateError(
            "opening_service_feasible must be a subset of the native mask"
        )
    opening.setflags(write=False)
    return opening


def _required_power(
    users: int,
    current_required_power_w: object,
) -> np.ndarray:
    try:
        raw = np.asarray(current_required_power_w)
        if raw.dtype.kind == "b":
            raise ValueError("Boolean power matrix")
        power = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise EEAxisV015C3ReferenceStateError(
            "current_required_power_w is malformed"
        ) from error
    if (
        power.shape != (users, NUM_ACTIONS)
        or not np.all(np.isfinite(power))
        or np.any(power < 0.0)
    ):
        raise EEAxisV015C3ReferenceStateError(
            "current_required_power_w must be finite nonnegative "
            f"shape ({users},{NUM_ACTIONS})"
        )
    power = np.array(power, dtype=np.float64, copy=True, order="C")
    power.setflags(write=False)
    return power


def _physical_key(table: SlotTable, action: int) -> tuple[int, int]:
    return int(table.norad_ids[action]), int(table.cell_ids[action])


def _reference_blocks(
    tables: tuple[SlotTable, ...],
    native: np.ndarray,
    references: np.ndarray,
    opening: np.ndarray,
    power: np.ndarray,
    *,
    pmax_w: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build all reference summaries before iterating over focal users."""

    users = len(tables)
    denominator = float(max(users - 1, 1))

    # This is the detached reference pass.  No focal-row calculation occurs
    # until every row has a validated physical key, opening bit, and capped
    # reference power.  Each user contributes at most once because c_v is one
    # action, even if its table contains duplicate physical slot entries.
    reference_opening = np.zeros(users, dtype=np.bool_)
    reference_keys: list[tuple[int, int] | None] = [None] * users
    reference_satellites = np.full(users, -1, dtype=np.int64)
    reference_power = np.zeros(users, dtype=np.float64)
    for uid in range(users):
        action = int(references[uid])
        if action == -1 or not bool(opening[uid, action]):
            continue
        key = _physical_key(tables[uid], action)
        reference_opening[uid] = True
        reference_keys[uid] = key
        reference_satellites[uid] = key[0]
        reference_power[uid] = min(float(power[uid, action]) / pmax_w, 1.0)

    beam = np.zeros((users, NUM_ACTIONS), dtype=np.float32)
    satellite = np.zeros_like(beam)
    gap = np.zeros_like(beam)
    for uid, table in enumerate(tables):
        for action_raw in np.flatnonzero(native[uid]).tolist():
            action = int(action_raw)
            candidate_key = _physical_key(table, action)
            candidate_satellite = candidate_key[0]
            peer_rows = [
                peer
                for peer in range(users)
                if peer != uid and bool(reference_opening[peer])
            ]
            same_beam = [
                peer
                for peer in peer_rows
                if reference_keys[peer] == candidate_key
            ]
            same_satellite = [
                peer
                for peer in peer_rows
                if int(reference_satellites[peer]) == candidate_satellite
            ]
            beam[uid, action] = np.float32(len(same_beam) / denominator)
            satellite[uid, action] = np.float32(len(same_satellite) / denominator)
            peer_max = max(
                (float(reference_power[peer]) for peer in same_beam),
                default=0.0,
            )
            focal_power = min(float(power[uid, action]) / pmax_w, 1.0)
            gap[uid, action] = np.float32(focal_power - peer_max)
    return beam, satellite, gap


def encode_ee_axis_v015_c3_reference_state(
    environment: StepEnvironment,
    observation: StepObservation,
    *,
    reference_actions: object,
    current_required_power_w: object,
    opening_service_feasible: object,
    interval_s: float,
    kappa_bits: float,
    pmax_w: float,
) -> EEAxisV015C3ReferenceStateObservation:
    """Encode the V0.14 prefix plus detached reference-conditioned C3 blocks.

    ``reference_actions`` must be one legal native action per user, with
    ``-1`` reserved for an all-empty native row.  ``opening_service_feasible``
    only determines which peer references contribute to the three blocks; it
    never replaces the native focal action mask.
    """

    pmax = _positive(pmax_w, field="pmax_w")
    tables, native = _anchor(environment, observation)
    references = _reference_vector(tables, native, reference_actions)
    opening = _opening_mask(native, opening_service_feasible)
    power = _required_power(len(tables), current_required_power_w)

    try:
        base = encode_ee_axis_v014_q3_state(
            environment,
            observation,
            interval_s=interval_s,
            kappa_bits=kappa_bits,
        )
    except (TypeError, ValueError, MCRLContractError, EEAxisV014Q3StateError) as error:
        raise EEAxisV015C3ReferenceStateError(
            f"V0.14 prefix cannot be encoded: {error}"
        ) from error

    if base.state_matrix.shape != (len(tables), V014_Q3_STATE_DIM):
        raise EEAxisV015C3ReferenceStateError(
            "V0.14 prefix has the wrong shape"
        )
    beam, satellite, gap = _reference_blocks(
        tables,
        native,
        references,
        opening,
        power,
        pmax_w=pmax,
    )
    prefix = np.asarray(base.state_matrix, dtype=np.float32)
    if (
        V015_C3_REFERENCE_LOCAL_PREFIX_DIM + V014_Q3_GLOBAL_FEATURES
        != V014_Q3_STATE_DIM
    ):
        raise EEAxisV015C3ReferenceStateError(
            "V0.14 action-local/global layout drifted"
        )
    values = np.concatenate(
        (
            prefix[:, :V015_C3_REFERENCE_LOCAL_PREFIX_DIM],
            beam,
            satellite,
            gap,
            prefix[:, V015_C3_REFERENCE_LOCAL_PREFIX_DIM:],
        ),
        axis=1,
        dtype=np.float32,
    )
    if values.shape != (len(tables), V015_C3_REFERENCE_STATE_DIM):
        raise EEAxisV015C3ReferenceStateError(
            "V0.15 reference C3 state assembly has the wrong shape"
        )
    if not np.array_equal(
        values[:, :V015_C3_REFERENCE_LOCAL_PREFIX_DIM],
        prefix[:, :V015_C3_REFERENCE_LOCAL_PREFIX_DIM],
    ) or not np.array_equal(
        values[:, V015_C3_REFERENCE_GLOBAL_START:],
        prefix[:, V015_C3_REFERENCE_LOCAL_PREFIX_DIM:],
    ):
        raise EEAxisV015C3ReferenceStateError(
            "V0.14 action-local or global values changed during assembly"
        )
    masks = np.array(native, dtype=np.bool_, copy=True, order="C")
    values.setflags(write=False)
    masks.setflags(write=False)
    result = EEAxisV015C3ReferenceStateObservation(
        schema=V015_C3_REFERENCE_STATE_SCHEMA,
        schema_sha256=V015_C3_REFERENCE_STATE_SCHEMA_SHA256,
        state_matrix=values,
        action_masks=masks,
        state_sha256=_matrix_sha256(values, masks),
    )
    result.verify()
    return result


encode_v015_c3_reference_state = encode_ee_axis_v015_c3_reference_state


__all__ = [
    "EEAxisV015C3ReferenceStateContractError",
    "EEAxisV015C3ReferenceStateError",
    "EEAxisV015C3ReferenceStateObservation",
    "V015_C3_REFERENCE_ACTION_BLOCKS",
    "V015_C3_REFERENCE_CONTEXT_BLOCKS",
    "V015_C3_REFERENCE_PREFIX_DIM",
    "V015_C3_REFERENCE_LOCAL_FEATURES",
    "V015_C3_REFERENCE_GLOBAL_FEATURES",
    "V015_C3_REFERENCE_GLOBAL_START",
    "V015_C3_REFERENCE_LOCAL_PREFIX_DIM",
    "V015_C3_REFERENCE_STATE_DIM",
    "V015_C3_REFERENCE_STATE_SCHEMA",
    "V015_C3_REFERENCE_STATE_SCHEMA_SHA256",
    "V015_C3_REFERENCE_BEAM_START",
    "V015_C3_REFERENCE_SATELLITE_START",
    "V015_C3_REFERENCE_POWER_GAP_START",
    "encode_ee_axis_v015_c3_reference_state",
    "encode_v015_c3_reference_state",
]
