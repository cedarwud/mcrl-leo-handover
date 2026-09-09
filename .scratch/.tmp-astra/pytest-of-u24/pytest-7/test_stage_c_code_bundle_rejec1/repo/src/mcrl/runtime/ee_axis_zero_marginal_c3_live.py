"""Exact current-slot measurements for zero-energy-supported C3 teachers.

This adapter owns physical counterfactual evaluation only.  It evaluates a
single frozen ``Q1 + O2`` joint reference and unilateral focal replacements
under the simulator's keyed common-random field.  The pure target formulas
live in :mod:`mcrl.runtime.ee_axis_zero_marginal_c3`.

Compatibility is intentionally strict.  A replacement is supported only
when its post-feasibility served vector, ordered active-beam and
active-satellite sets, per-beam RF powers, and canonical total network power
are bit-identical to the reference.  The resulting Boolean is target support,
never a second action mask.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import struct

import numpy as np

from ..env.action_contract import NUM_ACTIONS, assert_selected_actions_valid
from ..env.keyed_fading import KeyedFadingField
from ..env.step import ActionEvaluation, StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_ops3 import OPS3_INTERVAL_S


ZERO_MARGINAL_C3_LIVE_SCHEMA = (
    "multi-catfish-mcrl-v012-zero-energy-c3-live-measurement-v1"
)


class ZeroMarginalC3LiveError(MCRLContractError):
    """A live C3 measurement violated the frozen V0.12 boundary."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _array_bytes(value: np.ndarray) -> bytes:
    array = np.ascontiguousarray(value)
    return (
        array.dtype.str.encode("ascii")
        + repr(tuple(array.shape)).encode("ascii")
        + array.tobytes(order="C")
    )


@dataclass(frozen=True)
class CurrentPhysicsSignature:
    """The exact post-feasibility support relevant to current network power."""

    served_users: np.ndarray
    active_beam_keys: np.ndarray
    active_satellites: np.ndarray
    beam_power_w: np.ndarray
    system_power_w: float

    def __post_init__(self) -> None:
        served = np.asarray(self.served_users)
        beams = np.asarray(self.active_beam_keys)
        satellites = np.asarray(self.active_satellites)
        powers = np.asarray(self.beam_power_w, dtype=np.float64)
        if served.dtype != np.bool_ or served.ndim != 1:
            raise ZeroMarginalC3LiveError(
                "served_users must be a one-dimensional Boolean vector"
            )
        if (
            beams.ndim != 2
            or beams.shape[1:] != (2,)
            or not np.issubdtype(beams.dtype, np.integer)
            or np.issubdtype(beams.dtype, np.bool_)
        ):
            raise ZeroMarginalC3LiveError(
                "active_beam_keys must be an integer (B, 2) array"
            )
        if (
            satellites.ndim != 1
            or not np.issubdtype(satellites.dtype, np.integer)
            or np.issubdtype(satellites.dtype, np.bool_)
        ):
            raise ZeroMarginalC3LiveError(
                "active_satellites must be a one-dimensional integer vector"
            )
        if powers.shape != (beams.shape[0],) or not np.all(np.isfinite(powers)):
            raise ZeroMarginalC3LiveError(
                "beam_power_w must be finite and align with active beams"
            )
        if np.any(powers < 0.0):
            raise ZeroMarginalC3LiveError("beam_power_w must be non-negative")
        if not math.isfinite(float(self.system_power_w)) or float(
            self.system_power_w
        ) <= 0.0:
            raise ZeroMarginalC3LiveError(
                "system_power_w must be finite and positive"
            )
        if beams.shape[0] > 1:
            pairs = [tuple(int(v) for v in row) for row in beams.tolist()]
            if pairs != sorted(pairs) or len(pairs) != len(set(pairs)):
                raise ZeroMarginalC3LiveError(
                    "active_beam_keys must be unique canonical sorted pairs"
                )
        if satellites.size > 1:
            values = [int(value) for value in satellites.tolist()]
            if values != sorted(values) or len(values) != len(set(values)):
                raise ZeroMarginalC3LiveError(
                    "active_satellites must be unique and sorted"
                )
        expected_satellites = np.asarray(
            sorted({int(value) for value in beams[:, 0].tolist()}),
            dtype=np.int64,
        )
        if not np.array_equal(
            np.asarray(satellites, dtype=np.int64), expected_satellites
        ):
            raise ZeroMarginalC3LiveError(
                "active_satellites must equal the satellites in active_beam_keys"
            )
        object.__setattr__(
            self, "served_users", _readonly(served, dtype=np.bool_)
        )
        object.__setattr__(
            self, "active_beam_keys", _readonly(beams, dtype=np.int64)
        )
        object.__setattr__(
            self, "active_satellites", _readonly(satellites, dtype=np.int64)
        )
        object.__setattr__(
            self, "beam_power_w", _readonly(powers, dtype=np.float64)
        )
        object.__setattr__(self, "system_power_w", float(self.system_power_w))

    def bit_exact_equal(self, other: object) -> bool:
        """Return exact-byte equality; no scientific tolerance is applied."""

        if not isinstance(other, CurrentPhysicsSignature):
            return False
        return all(self.compatibility_components(other))

    def compatibility_components(
        self, other: object
    ) -> tuple[bool, bool, bool, bool, bool]:
        """Return served/beam/satellite/RF/network exact-equality flags."""

        if not isinstance(other, CurrentPhysicsSignature):
            return (False, False, False, False, False)
        return (
            _array_bytes(self.served_users) == _array_bytes(other.served_users),
            _array_bytes(self.active_beam_keys)
            == _array_bytes(other.active_beam_keys),
            _array_bytes(self.active_satellites)
            == _array_bytes(other.active_satellites),
            _array_bytes(self.beam_power_w) == _array_bytes(other.beam_power_w),
            struct.pack(">d", self.system_power_w)
            == struct.pack(">d", other.system_power_w),
        )

    @property
    def sha256(self) -> str:
        digest = hashlib.sha256()
        for value in (
            self.served_users,
            self.active_beam_keys,
            self.active_satellites,
            self.beam_power_w,
        ):
            digest.update(_array_bytes(value))
        digest.update(struct.pack(">d", self.system_power_w))
        return digest.hexdigest()


def physics_signature(evaluation: ActionEvaluation) -> CurrentPhysicsSignature:
    """Extract the frozen support signature from one canonical evaluation."""

    if not isinstance(evaluation, ActionEvaluation):
        raise ZeroMarginalC3LiveError("evaluation must be an ActionEvaluation")
    radiating = evaluation.radiating
    beams = np.column_stack((radiating.norad_ids, radiating.cell_ids)).astype(
        np.int64, copy=False
    )
    satellites = np.asarray(
        sorted({int(value) for value in radiating.norad_ids.tolist()}),
        dtype=np.int64,
    )
    return CurrentPhysicsSignature(
        served_users=np.asarray(evaluation.resolution.served, dtype=np.bool_),
        active_beam_keys=beams,
        active_satellites=satellites,
        beam_power_w=np.asarray(radiating.power_w, dtype=np.float64),
        system_power_w=float(evaluation.system_power_w),
    )


@dataclass(frozen=True)
class ZeroMarginalC3Measurements:
    """Action-aligned physical inputs for the pure ZR and HR equations."""

    reference_actions: np.ndarray
    legal_mask: np.ndarray
    reference_rate_bps: np.ndarray
    candidate_rate_bps: np.ndarray
    removed_rate_bps: np.ndarray | None
    replacement_delta_bits: np.ndarray
    insertion_delta_bits: np.ndarray | None
    compatible: np.ndarray
    served_equal: np.ndarray
    active_beams_equal: np.ndarray
    active_satellites_equal: np.ndarray
    rf_power_equal: np.ndarray
    network_power_equal: np.ndarray
    reference_signature_sha256: str
    counterfactual_evaluations: int
    interval_s: float
    schema: str = ZERO_MARGINAL_C3_LIVE_SCHEMA

    def __post_init__(self) -> None:
        reference = np.asarray(self.reference_actions)
        legal = np.asarray(self.legal_mask)
        reference_rate = np.asarray(self.reference_rate_bps, dtype=np.float64)
        candidate_rate = np.asarray(self.candidate_rate_bps, dtype=np.float64)
        replacement = np.asarray(self.replacement_delta_bits, dtype=np.float64)
        compatible = np.asarray(self.compatible)
        if (
            reference.ndim != 1
            or not np.issubdtype(reference.dtype, np.integer)
            or np.issubdtype(reference.dtype, np.bool_)
        ):
            raise ZeroMarginalC3LiveError(
                "reference_actions must be a one-dimensional integer vector"
            )
        users = reference.size
        if legal.dtype != np.bool_ or legal.shape != (users, NUM_ACTIONS):
            raise ZeroMarginalC3LiveError(
                f"legal_mask must be Boolean shape ({users}, {NUM_ACTIONS})"
            )
        if reference_rate.shape != (users, users) or not np.all(
            np.isfinite(reference_rate)
        ) or np.any(reference_rate < 0.0):
            raise ZeroMarginalC3LiveError(
                "reference_rate_bps must be finite non-negative (U, U)"
            )
        if candidate_rate.shape != (users, NUM_ACTIONS, users) or not np.all(
            np.isfinite(candidate_rate)
        ) or np.any(candidate_rate < 0.0):
            raise ZeroMarginalC3LiveError(
                "candidate_rate_bps must be finite non-negative (U, 28, U)"
            )
        if replacement.shape != (users, NUM_ACTIONS, users) or not np.all(
            np.isfinite(replacement)
        ):
            raise ZeroMarginalC3LiveError(
                "replacement_delta_bits must be finite (U, 28, U)"
            )
        if compatible.dtype != np.bool_ or compatible.shape != legal.shape:
            raise ZeroMarginalC3LiveError(
                "compatible must be Boolean and action-aligned"
            )
        removed = self.removed_rate_bps
        if removed is not None:
            removed = np.asarray(removed, dtype=np.float64)
            if removed.shape != (users, users) or not np.all(
                np.isfinite(removed)
            ) or np.any(removed < 0.0):
                raise ZeroMarginalC3LiveError(
                    "removed_rate_bps must be finite non-negative (U, U)"
                )
        insertion = self.insertion_delta_bits
        if insertion is not None:
            insertion = np.asarray(insertion, dtype=np.float64)
            if insertion.shape != replacement.shape or not np.all(
                np.isfinite(insertion)
            ):
                raise ZeroMarginalC3LiveError(
                    "insertion_delta_bits must be finite (U, 28, U)"
                )
        if (removed is None) != (insertion is None):
            raise ZeroMarginalC3LiveError(
                "removed rates and insertion deltas must be present together"
            )
        if np.any(replacement[~legal] != 0.0):
            raise ZeroMarginalC3LiveError(
                "replacement deltas must be zero outside the safe mask"
            )
        if insertion is not None and np.any(insertion[~legal] != 0.0):
            raise ZeroMarginalC3LiveError(
                "insertion deltas must be zero outside the safe mask"
            )
        if np.any(compatible[~legal]):
            raise ZeroMarginalC3LiveError(
                "compatibility must be false outside the safe mask"
            )
        component_values: dict[str, np.ndarray] = {}
        for field in (
            "served_equal",
            "active_beams_equal",
            "active_satellites_equal",
            "rf_power_equal",
            "network_power_equal",
        ):
            value = np.asarray(getattr(self, field))
            if value.dtype != np.bool_ or value.shape != legal.shape:
                raise ZeroMarginalC3LiveError(
                    f"{field} must be Boolean and action-aligned"
                )
            if np.any(value[~legal]):
                raise ZeroMarginalC3LiveError(
                    f"{field} must be false outside the safe mask"
                )
            component_values[field] = value
        conjunction = (
            component_values["served_equal"]
            & component_values["active_beams_equal"]
            & component_values["active_satellites_equal"]
            & component_values["rf_power_equal"]
            & component_values["network_power_equal"]
        )
        if not np.array_equal(compatible, conjunction):
            raise ZeroMarginalC3LiveError(
                "compatible is not the conjunction of exact support components"
            )
        for uid, action in enumerate(reference.tolist()):
            if not 0 <= int(action) < NUM_ACTIONS or not bool(legal[uid, int(action)]):
                raise ZeroMarginalC3LiveError(
                    "every reference action must be safe and native"
                )
            if np.any(replacement[uid, int(action)] != 0.0):
                raise ZeroMarginalC3LiveError(
                    "reference replacement delta must be exact zero"
                )
            if reference_rate[uid, uid] != 0.0 or np.any(
                candidate_rate[uid, :, uid] != 0.0
            ):
                raise ZeroMarginalC3LiveError(
                    "focal rates must be removed from every victim panel"
                )
            if removed is not None and removed[uid, uid] != 0.0:
                raise ZeroMarginalC3LiveError(
                    "focal rate must be removed from its insertion baseline"
                )
            if not bool(compatible[uid, int(action)]):
                raise ZeroMarginalC3LiveError(
                    "every reference action must be exactly compatible"
                )
        if (
            not isinstance(self.reference_signature_sha256, str)
            or len(self.reference_signature_sha256) != 64
        ):
            raise ZeroMarginalC3LiveError(
                "reference_signature_sha256 must be a SHA-256 string"
            )
        if (
            type(self.counterfactual_evaluations) is not int
            or self.counterfactual_evaluations < 1
        ):
            raise ZeroMarginalC3LiveError(
                "counterfactual_evaluations must be a positive integer"
            )
        interval = float(self.interval_s)
        if not math.isfinite(interval) or interval <= 0.0:
            raise ZeroMarginalC3LiveError("interval_s must be finite and positive")
        expected_replacement = interval * (
            candidate_rate - reference_rate[:, None, :]
        )
        expected_replacement = np.where(
            legal[:, :, None], expected_replacement, 0.0
        )
        if not np.array_equal(replacement, expected_replacement):
            raise ZeroMarginalC3LiveError(
                "replacement deltas do not match the sealed rate panels"
            )
        if insertion is not None:
            assert removed is not None
            expected_insertion = interval * (
                candidate_rate - removed[:, None, :]
            )
            expected_insertion = np.where(
                legal[:, :, None], expected_insertion, 0.0
            )
            if not np.array_equal(insertion, expected_insertion):
                raise ZeroMarginalC3LiveError(
                    "insertion deltas do not match the sealed rate panels"
                )
        if self.schema != ZERO_MARGINAL_C3_LIVE_SCHEMA:
            raise ZeroMarginalC3LiveError("live measurement schema is stale")
        object.__setattr__(
            self, "reference_actions", _readonly(reference, dtype=np.int64)
        )
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))
        object.__setattr__(
            self, "reference_rate_bps", _readonly(reference_rate, dtype=np.float64)
        )
        object.__setattr__(
            self, "candidate_rate_bps", _readonly(candidate_rate, dtype=np.float64)
        )
        object.__setattr__(
            self,
            "removed_rate_bps",
            None if removed is None else _readonly(removed, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "replacement_delta_bits",
            _readonly(replacement, dtype=np.float64),
        )
        object.__setattr__(
            self,
            "insertion_delta_bits",
            None if insertion is None else _readonly(insertion, dtype=np.float64),
        )
        object.__setattr__(
            self, "compatible", _readonly(compatible, dtype=np.bool_)
        )
        for field, value in component_values.items():
            object.__setattr__(self, field, _readonly(value, dtype=np.bool_))
        object.__setattr__(self, "interval_s", interval)


def _assert_anchor(
    environment: StepEnvironment, observation: StepObservation
) -> None:
    if not isinstance(environment, StepEnvironment):
        raise ZeroMarginalC3LiveError("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise ZeroMarginalC3LiveError("observation must be StepObservation")
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise ZeroMarginalC3LiveError("observation is not the current sealed anchor")
    if observation.step_index != environment.driver.step_index:
        raise ZeroMarginalC3LiveError(
            "observation step does not match the environment"
        )
    if not np.array_equal(observation.masks, observation.candidates.masks):
        raise ZeroMarginalC3LiveError(
            "observation masks disagree with candidate tables"
        )
    if (
        not bool(environment.physics.fading_enabled)
        or not isinstance(getattr(environment, "_fading_field", None), KeyedFadingField)
    ):
        raise ZeroMarginalC3LiveError(
            "zero-energy C3 requires the canonical keyed fading field"
        )


def measure_zero_marginal_c3(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    reference_actions: object,
    rng: np.random.Generator,
    include_insertion: bool,
    interval_s: float = OPS3_INTERVAL_S,
) -> ZeroMarginalC3Measurements:
    """Measure exact unilateral replacement and optional insertion effects."""

    _assert_anchor(environment, observation)
    if not isinstance(rng, np.random.Generator):
        raise ZeroMarginalC3LiveError("rng must be numpy.random.Generator")
    if type(include_insertion) is not bool:
        raise ZeroMarginalC3LiveError("include_insertion must be Boolean")
    if not math.isfinite(float(interval_s)) or float(interval_s) <= 0.0:
        raise ZeroMarginalC3LiveError("interval_s must be finite and positive")
    try:
        reference = assert_selected_actions_valid(
            np.asarray(reference_actions), observation.candidates.slot_tables
        )
    except (MCRLContractError, TypeError, ValueError) as error:
        raise ZeroMarginalC3LiveError(
            "reference_actions are not a safe deployment vector"
        ) from error

    users = observation.num_users
    legal = np.asarray(observation.masks, dtype=np.bool_)
    if reference.shape != (users,) or not np.all(np.any(legal, axis=1)):
        raise ZeroMarginalC3LiveError(
            "V0.12 needs one safe native action for every focal user"
        )
    reference_evaluation = environment.evaluate_actions(reference, rng)
    reference_rates = np.asarray(
        reference_evaluation.link_rate_bps, dtype=np.float64
    )
    reference_signature = physics_signature(reference_evaluation)
    evaluations = 1

    replacement = np.zeros((users, NUM_ACTIONS, users), dtype=np.float64)
    reference_rate_panel = np.repeat(
        reference_rates[None, :], users, axis=0
    ).astype(np.float64, copy=True)
    for uid in range(users):
        reference_rate_panel[uid, uid] = 0.0
    candidate_rate_panel = np.zeros(
        (users, NUM_ACTIONS, users), dtype=np.float64
    )
    removed_rate_panel = (
        np.zeros((users, users), dtype=np.float64) if include_insertion else None
    )
    insertion = (
        np.zeros_like(replacement, dtype=np.float64) if include_insertion else None
    )
    compatible = np.zeros((users, NUM_ACTIONS), dtype=np.bool_)
    served_equal = np.zeros_like(compatible)
    active_beams_equal = np.zeros_like(compatible)
    active_satellites_equal = np.zeros_like(compatible)
    rf_power_equal = np.zeros_like(compatible)
    network_power_equal = np.zeros_like(compatible)
    interval = float(interval_s)

    for uid in range(users):
        reference_action = int(reference[uid])
        removed_rates: np.ndarray | None = None
        if include_insertion:
            removed_evaluation = environment.evaluate_actions_without_user(
                reference, rng, focal_user=uid
            )
            removed_rates = np.asarray(
                removed_evaluation.link_rate_bps, dtype=np.float64
            )
            assert removed_rate_panel is not None
            removed_rate_panel[uid] = removed_rates
            removed_rate_panel[uid, uid] = 0.0
            evaluations += 1
        for action_raw in np.flatnonzero(legal[uid]).tolist():
            action = int(action_raw)
            if action == reference_action:
                candidate_evaluation = reference_evaluation
            else:
                candidate = np.array(reference, dtype=np.int64, copy=True)
                candidate[uid] = action
                if np.count_nonzero(candidate != reference) != 1:
                    raise ZeroMarginalC3LiveError(
                        "unilateral branch changed more than the focal action"
                    )
                candidate_evaluation = environment.evaluate_actions(candidate, rng)
                evaluations += 1
            candidate_rates = np.asarray(
                candidate_evaluation.link_rate_bps, dtype=np.float64
            )
            replacement[uid, action] = interval * (
                candidate_rates - reference_rates
            )
            replacement[uid, action, uid] = 0.0
            candidate_rate_panel[uid, action] = candidate_rates
            candidate_rate_panel[uid, action, uid] = 0.0
            if insertion is not None:
                assert removed_rates is not None
                insertion[uid, action] = interval * (
                    candidate_rates - removed_rates
                )
                insertion[uid, action, uid] = 0.0
            components = reference_signature.compatibility_components(
                physics_signature(candidate_evaluation)
            )
            (
                served_equal[uid, action],
                active_beams_equal[uid, action],
                active_satellites_equal[uid, action],
                rf_power_equal[uid, action],
                network_power_equal[uid, action],
            ) = components
            compatible[uid, action] = all(components)

    return ZeroMarginalC3Measurements(
        reference_actions=reference,
        legal_mask=legal,
        reference_rate_bps=reference_rate_panel,
        candidate_rate_bps=candidate_rate_panel,
        removed_rate_bps=removed_rate_panel,
        replacement_delta_bits=replacement,
        insertion_delta_bits=insertion,
        compatible=compatible,
        served_equal=served_equal,
        active_beams_equal=active_beams_equal,
        active_satellites_equal=active_satellites_equal,
        rf_power_equal=rf_power_equal,
        network_power_equal=network_power_equal,
        reference_signature_sha256=reference_signature.sha256,
        counterfactual_evaluations=evaluations,
        interval_s=interval,
    )


__all__ = [
    "ZERO_MARGINAL_C3_LIVE_SCHEMA",
    "CurrentPhysicsSignature",
    "ZeroMarginalC3LiveError",
    "ZeroMarginalC3Measurements",
    "measure_zero_marginal_c3",
    "physics_signature",
]
