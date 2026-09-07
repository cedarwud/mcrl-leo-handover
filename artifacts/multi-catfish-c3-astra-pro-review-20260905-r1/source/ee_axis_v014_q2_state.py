"""Target-free deployable state wrapper for the V0.14 OPS3-Q2 learner.

OPS3 emits a deterministic forecast sidecar with 16 action-local features for
each of the 28 native actions.  The same object also carries teacher targets
for training receipts.  This boundary copies *only* ``features`` and the
explicit legal mask into an immutable feature-major learner state; ``z2``,
``q2_values``, the gauge action, and realized outcomes are never read.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json

import numpy as np

from ..env.action_contract import NUM_ACTIONS
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3_FEATURE_DIM, OPS3_SCHEMA, OPS3Surface


V014_Q2_LOCAL_FEATURES = OPS3_FEATURE_DIM
V014_Q2_GLOBAL_FEATURES = 0
V014_Q2_STATE_DIM = V014_Q2_LOCAL_FEATURES * NUM_ACTIONS
V014_Q2_STATE_SCHEMA = "multi-catfish-mcrl-v014-ops3-q2-state-v1"
V014_Q2_STATE_SCHEMA_VERSION = 1
V014_Q2_FEATURE_NAMES = (
    "background_load",
    "background_power",
    "beam_active",
    "satellite_active",
    "h1_valid",
    "h1_persistence",
    "h1_required_power_ratio",
    "h1_log1p_sinr",
    "h2_valid",
    "h2_persistence",
    "h2_required_power_ratio",
    "h2_log1p_sinr",
    "h3_valid",
    "h3_persistence",
    "h3_required_power_ratio",
    "h3_log1p_sinr",
)


def _schema_payload() -> dict[str, object]:
    return {
        "schema": V014_Q2_STATE_SCHEMA,
        "schema_version": V014_Q2_STATE_SCHEMA_VERSION,
        "source_schema": OPS3_SCHEMA,
        "action_dim": NUM_ACTIONS,
        "local_feature_dim": V014_Q2_LOCAL_FEATURES,
        "global_feature_dim": V014_Q2_GLOBAL_FEATURES,
        "state_dim": V014_Q2_STATE_DIM,
        "layout": "feature-major",
        "feature_names": list(V014_Q2_FEATURE_NAMES),
        "forbidden_inputs": [
            "z2-bits",
            "q2-values",
            "reference-action",
            "realized-rate-power-or-sinr",
            "selected-actions-or-outcomes",
            "q1-or-q3-values-ranks-or-actions",
            "target-values-or-signs",
        ],
    }


V014_Q2_STATE_SCHEMA_SHA256 = hashlib.sha256(
    json.dumps(
        _schema_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
).hexdigest()


class EEAxisV014Q2StateError(MCRLContractError):
    """An OPS3 feature sidecar is missing, stale, or unsafe for Q2."""


def _payload_sha256(states: np.ndarray, masks: np.ndarray) -> str:
    payload = {
        "schema_sha256": V014_Q2_STATE_SCHEMA_SHA256,
        "state_float32_hex": [float(value).hex() for value in states.ravel()],
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
class EEAxisV014Q2StateObservation:
    """Immutable batch of target-free Q2 states and legal masks."""

    schema: str
    schema_sha256: str
    state_matrix: np.ndarray
    action_masks: np.ndarray
    state_sha256: str

    def verify(self) -> str:
        if self.schema != V014_Q2_STATE_SCHEMA:
            raise EEAxisV014Q2StateError("unsupported V0.14 Q2 state schema")
        if self.schema_sha256 != V014_Q2_STATE_SCHEMA_SHA256:
            raise EEAxisV014Q2StateError("V0.14 Q2 state schema digest drifted")
        states = np.asarray(self.state_matrix)
        masks = np.asarray(self.action_masks)
        if states.ndim != 2 or states.shape[1] != V014_Q2_STATE_DIM:
            raise EEAxisV014Q2StateError(
                f"state_matrix must have shape (batch,{V014_Q2_STATE_DIM})"
            )
        if masks.dtype != np.bool_ or masks.shape != (states.shape[0], NUM_ACTIONS):
            raise EEAxisV014Q2StateError(
                f"action_masks must be Boolean shape (batch,{NUM_ACTIONS})"
            )
        if states.shape[0] < 1 or not np.all(np.any(masks, axis=1)):
            raise EEAxisV014Q2StateError("every Q2 state needs a legal action")
        if not np.all(np.isfinite(states)):
            raise EEAxisV014Q2StateError("Q2 state values must be finite")
        if states.flags.writeable or masks.flags.writeable:
            raise EEAxisV014Q2StateError("Q2 state arrays must be immutable")
        actual = _payload_sha256(states, masks)
        if actual != self.state_sha256:
            raise EEAxisV014Q2StateError("Q2 state digest disagrees with its arrays")
        return actual


def encode_ee_axis_v014_q2_states(
    surfaces: Sequence[OPS3Surface],
) -> EEAxisV014Q2StateObservation:
    """Copy only OPS3 forecast features/masks into learner-ready states."""

    try:
        rows = tuple(surfaces)
    except TypeError as error:
        raise EEAxisV014Q2StateError("surfaces must be a sequence") from error
    if not rows:
        raise EEAxisV014Q2StateError("surfaces must be nonempty")

    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    for surface in rows:
        if not isinstance(surface, OPS3Surface) or surface.schema != OPS3_SCHEMA:
            raise EEAxisV014Q2StateError("Q2 input must be a current OPS3 surface")
        features = np.asarray(surface.features)
        legal = np.asarray(surface.legal_mask)
        if (
            features.shape != (NUM_ACTIONS, V014_Q2_LOCAL_FEATURES)
            or not np.all(np.isfinite(features))
        ):
            raise EEAxisV014Q2StateError("OPS3 features are malformed")
        if legal.dtype != np.bool_ or legal.shape != (NUM_ACTIONS,):
            raise EEAxisV014Q2StateError("OPS3 legal mask is malformed")
        if not bool(np.any(legal)):
            raise EEAxisV014Q2StateError("every Q2 surface needs a legal action")
        states.append(features.astype(np.float32, copy=True).T.reshape(-1))
        masks.append(np.array(legal, dtype=np.bool_, copy=True))

    state_matrix = np.stack(states)
    action_masks = np.stack(masks)
    state_matrix.setflags(write=False)
    action_masks.setflags(write=False)
    result = EEAxisV014Q2StateObservation(
        schema=V014_Q2_STATE_SCHEMA,
        schema_sha256=V014_Q2_STATE_SCHEMA_SHA256,
        state_matrix=state_matrix,
        action_masks=action_masks,
        state_sha256=_payload_sha256(state_matrix, action_masks),
    )
    result.verify()
    return result


__all__ = [
    "EEAxisV014Q2StateError",
    "EEAxisV014Q2StateObservation",
    "V014_Q2_FEATURE_NAMES",
    "V014_Q2_GLOBAL_FEATURES",
    "V014_Q2_LOCAL_FEATURES",
    "V014_Q2_STATE_DIM",
    "V014_Q2_STATE_SCHEMA",
    "V014_Q2_STATE_SCHEMA_SHA256",
    "encode_ee_axis_v014_q2_states",
]
