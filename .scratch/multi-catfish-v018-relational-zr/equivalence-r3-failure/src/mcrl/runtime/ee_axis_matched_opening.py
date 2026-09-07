"""Exact matched-opening EE surfaces for one frozen joint background.

The background action vector is chosen by the caller before this module is
entered.  For every focal user and every legal action, only that focal action
is replaced and the canonical current-slot simulator physics is evaluated.
The resulting opening surplus is split without overlap into

* ``O1``: focal delivered bits minus all opening network-energy cost; and
* ``O3``: delivered-bit externality on every non-focal user.

The same ``O3`` surface can therefore be reused by every ablation arm at an
anchor.  Rebuilding it around an arm-specific action vector would change the
component being ablated and is deliberately outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..env.action_contract import NUM_ACTIONS, assert_selected_actions_valid
from ..env.keyed_fading import KeyedFadingField
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3_INTERVAL_S, OPS3_KAPPA_BITS


MATCHED_OPENING_SCHEMA = "multi-catfish-mcrl-c3-matched-opening-surface-v1"


class MatchedOpeningError(MCRLContractError):
    """A matched-opening input or result violates the frozen contract."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class MatchedOpeningSurfaces:
    """One immutable pair of exact O1/O3 oracle surfaces."""

    reference_joint_actions: np.ndarray
    legal_mask: np.ndarray
    focal_delta_bits: np.ndarray
    nonfocal_delta_bits: np.ndarray
    network_delta_energy_j: np.ndarray
    z1_bits: np.ndarray
    z3_bits: np.ndarray
    system_surplus_bits: np.ndarray
    identity_residual_bits: np.ndarray
    q1_values: np.ndarray
    q3_values: np.ndarray
    lambda_bits_per_j: float
    interval_s: float
    kappa_bits: float
    schema: str = MATCHED_OPENING_SCHEMA

    def __post_init__(self) -> None:
        reference = np.asarray(self.reference_joint_actions)
        legal = np.asarray(self.legal_mask)
        if (
            reference.ndim != 1
            or not np.issubdtype(reference.dtype, np.integer)
            or np.issubdtype(reference.dtype, np.bool_)
        ):
            raise MatchedOpeningError(
                "reference_joint_actions must be a one-dimensional integer vector"
            )
        expected = (reference.size, NUM_ACTIONS)
        if legal.dtype != np.bool_ or legal.shape != expected:
            raise MatchedOpeningError(
                f"legal_mask must be Boolean shape {expected}"
            )
        for field in (
            "focal_delta_bits",
            "nonfocal_delta_bits",
            "network_delta_energy_j",
            "z1_bits",
            "z3_bits",
            "system_surplus_bits",
            "identity_residual_bits",
            "q1_values",
            "q3_values",
        ):
            value = np.asarray(getattr(self, field), dtype=np.float64)
            if value.shape != expected or not np.all(np.isfinite(value)):
                raise MatchedOpeningError(f"{field} must be finite shape {expected}")
            if np.any(value[~legal] != 0.0):
                raise MatchedOpeningError(f"{field} must be zero outside the safe mask")
            object.__setattr__(self, field, _readonly(value, dtype=np.float64))
        for field in ("lambda_bits_per_j", "interval_s", "kappa_bits"):
            value = float(getattr(self, field))
            if not math.isfinite(value) or value <= 0.0:
                raise MatchedOpeningError(f"{field} must be finite and positive")
        if self.schema != MATCHED_OPENING_SCHEMA:
            raise MatchedOpeningError("matched-opening schema is stale")

        for uid, reference_action in enumerate(reference.tolist()):
            if bool(np.any(legal[uid])):
                if not 0 <= int(reference_action) < NUM_ACTIONS:
                    raise MatchedOpeningError("nonempty rows need a native reference")
                if not bool(legal[uid, int(reference_action)]):
                    raise MatchedOpeningError("each nonempty reference must be legal")
                for field in (
                    self.focal_delta_bits,
                    self.nonfocal_delta_bits,
                    self.network_delta_energy_j,
                    self.z1_bits,
                    self.z3_bits,
                    self.system_surplus_bits,
                    self.identity_residual_bits,
                    self.q1_values,
                    self.q3_values,
                ):
                    if float(field[uid, int(reference_action)]) != 0.0:
                        raise MatchedOpeningError(
                            "every reference row must be exact zero"
                        )
            elif int(reference_action) != -1:
                raise MatchedOpeningError("empty rows require reference action -1")

        magnitude = np.maximum(
            1.0,
            np.abs(self.z1_bits) + np.abs(self.z3_bits),
        )
        tolerance = 512.0 * np.finfo(np.float64).eps * magnitude
        if np.any(np.abs(self.identity_residual_bits) > tolerance):
            raise MatchedOpeningError("O1+O3 opening identity lost precision")

        object.__setattr__(
            self,
            "reference_joint_actions",
            _readonly(reference, dtype=np.int64),
        )
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))


def _assert_anchor(
    environment: StepEnvironment, observation: StepObservation
) -> None:
    if not isinstance(environment, StepEnvironment):
        raise MatchedOpeningError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise MatchedOpeningError("observation must be StepObservation")
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise MatchedOpeningError("observation is not the current sealed anchor")
    if observation.step_index != environment.driver.step_index:
        raise MatchedOpeningError("observation step does not match the environment")
    if not np.array_equal(observation.masks, observation.candidates.masks):
        raise MatchedOpeningError("observation masks disagree with candidate tables")
    if (
        not bool(environment.physics.fading_enabled)
        or not isinstance(getattr(environment, "_fading_field", None), KeyedFadingField)
    ):
        raise MatchedOpeningError("matched opening requires the keyed fading field")


def build_matched_opening_surfaces(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    reference_joint_actions: object,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
) -> MatchedOpeningSurfaces:
    """Evaluate exact unilateral opening O1/O3 surfaces around one background."""

    _assert_anchor(environment, observation)
    if not isinstance(rng, np.random.Generator):
        raise MatchedOpeningError("rng must be numpy.random.Generator")
    for field, value in (
        ("lambda_bits_per_j", lambda_bits_per_j),
        ("interval_s", interval_s),
        ("kappa_bits", kappa_bits),
    ):
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise MatchedOpeningError(f"{field} must be finite and positive")

    raw_reference = np.asarray(reference_joint_actions)
    users = observation.num_users
    if (
        raw_reference.shape != (users,)
        or not np.issubdtype(raw_reference.dtype, np.integer)
        or np.issubdtype(raw_reference.dtype, np.bool_)
    ):
        raise MatchedOpeningError(
            f"reference_joint_actions must be integer shape ({users},)"
        )
    try:
        reference = assert_selected_actions_valid(
            np.array(raw_reference, dtype=np.int64, copy=True),
            observation.candidates.slot_tables,
        )
    except (MCRLContractError, TypeError, ValueError) as error:
        raise MatchedOpeningError("reference joint action is not safe") from error

    legal = np.asarray(observation.masks, dtype=np.bool_)
    shape = (users, NUM_ACTIONS)
    focal_bits = np.zeros(shape, dtype=np.float64)
    nonfocal_bits = np.zeros(shape, dtype=np.float64)
    delta_energy = np.zeros(shape, dtype=np.float64)
    z1 = np.zeros(shape, dtype=np.float64)
    z3 = np.zeros(shape, dtype=np.float64)
    total = np.zeros(shape, dtype=np.float64)

    reference_evaluation = environment.evaluate_actions(reference, rng)
    reference_rates = np.asarray(reference_evaluation.link_rate_bps, dtype=np.float64)
    reference_power = float(reference_evaluation.system_power_w)
    interval = float(interval_s)
    multiplier = float(lambda_bits_per_j)

    for uid in range(users):
        reference_action = int(reference[uid])
        for action in np.flatnonzero(legal[uid]).tolist():
            action = int(action)
            if action == reference_action:
                continue
            candidate = np.array(reference, copy=True)
            candidate[uid] = action
            evaluation = environment.evaluate_actions(candidate, rng)
            rate_delta = np.asarray(evaluation.link_rate_bps, dtype=np.float64) - reference_rates
            focal_bits[uid, action] = interval * float(rate_delta[uid])
            nonfocal_bits[uid, action] = interval * math.fsum(
                float(rate_delta[v]) for v in range(users) if v != uid
            )
            delta_energy[uid, action] = interval * (
                float(evaluation.system_power_w) - reference_power
            )
            z1[uid, action] = (
                focal_bits[uid, action]
                - multiplier * delta_energy[uid, action]
            )
            z3[uid, action] = nonfocal_bits[uid, action]
            total[uid, action] = interval * math.fsum(
                float(value) for value in rate_delta
            ) - multiplier * delta_energy[uid, action]

    residual = z1 + z3 - total
    q1 = z1 / float(kappa_bits)
    q3 = z3 / float(kappa_bits)
    return MatchedOpeningSurfaces(
        reference_joint_actions=reference,
        legal_mask=legal,
        focal_delta_bits=focal_bits,
        nonfocal_delta_bits=nonfocal_bits,
        network_delta_energy_j=delta_energy,
        z1_bits=z1,
        z3_bits=z3,
        system_surplus_bits=total,
        identity_residual_bits=residual,
        q1_values=q1,
        q3_values=q3,
        lambda_bits_per_j=multiplier,
        interval_s=interval,
        kappa_bits=float(kappa_bits),
    )


__all__ = [
    "MATCHED_OPENING_SCHEMA",
    "MatchedOpeningError",
    "MatchedOpeningSurfaces",
    "build_matched_opening_surfaces",
]
