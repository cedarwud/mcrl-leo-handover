"""Exact joint-response C3 oracle helpers.

This module deliberately has no episode, learner, checkpoint, seed, or arm
knowledge.  It is a pure adapter over ``StepEnvironment.evaluate_actions`` at
one sealed opening anchor.  Callers provide the frozen Q1/O2 score surfaces
and any keyed user permutation; this module only constructs exact physical C3
targets and verifies the mechanics required by the ordered-oracle contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS, assert_selected_actions_valid
from ..env.keyed_fading import KeyedFadingField
from ..env.step import StepEnvironment, StepObservation
from ..errors import MCRLContractError
from .ee_axis_matched_opening import MatchedOpeningSurfaces, build_matched_opening_surfaces
from .ee_axis_ops3 import OPS3_INTERVAL_S, OPS3_KAPPA_BITS


JOINT_C3_SCHEMA = "multi-catfish-mcrl-joint-c3-runtime-v1"


class JointC3Error(MCRLContractError):
    """A V0.11 joint-C3 input or mechanics result is invalid."""


def _readonly(value: object, *, dtype: np.dtype | type) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _finite_positive(value: object, *, field: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise JointC3Error(f"{field} must be finite and positive")
    return result


def _assert_anchor(environment: StepEnvironment, observation: StepObservation) -> None:
    if not isinstance(environment, StepEnvironment):
        raise JointC3Error("environment must be StepEnvironment")
    if not isinstance(observation, StepObservation):
        raise JointC3Error("observation must be StepObservation")
    if getattr(environment, "_candidates", None) is not observation.candidates:
        raise JointC3Error("observation is not the current sealed anchor")
    if observation.step_index != environment.driver.step_index:
        raise JointC3Error("observation step does not match the environment")
    if not np.array_equal(observation.masks, observation.candidates.masks):
        raise JointC3Error("observation masks disagree with candidate tables")
    if (
        not bool(environment.physics.fading_enabled)
        or not isinstance(getattr(environment, "_fading_field", None), KeyedFadingField)
    ):
        raise JointC3Error("joint C3 requires the keyed fading field")


def _safe_actions(observation: StepObservation, actions: object, *, field: str) -> np.ndarray:
    raw = np.asarray(actions)
    if (
        raw.shape != (observation.num_users,)
        or not np.issubdtype(raw.dtype, np.integer)
        or np.issubdtype(raw.dtype, np.bool_)
    ):
        raise JointC3Error(f"{field} must be integer shape ({observation.num_users},)")
    try:
        return assert_selected_actions_valid(
            np.array(raw, dtype=np.int64, copy=True), observation.candidates.slot_tables
        )
    except (MCRLContractError, TypeError, ValueError) as error:
        raise JointC3Error(f"{field} is not safe") from error


def _score_matrix(value: object, *, field: str, users: int) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (users, NUM_ACTIONS) or not np.all(np.isfinite(result)):
        raise JointC3Error(f"{field} must be finite shape ({users}, {NUM_ACTIONS})")
    return np.array(result, copy=True, dtype=np.float64, order="C")


def select_masked_actions(q1_values: object, o2_values: object, o3_values: object, legal_mask: object) -> np.ndarray:
    """One unweighted, lowest-native-index masked argmax per user."""

    raw_mask = np.asarray(legal_mask)
    if raw_mask.ndim != 2 or raw_mask.shape[1:] != (NUM_ACTIONS,) or raw_mask.dtype != np.bool_:
        raise JointC3Error("legal_mask must be Boolean shape (users, 28)")
    users = int(raw_mask.shape[0])
    q1 = _score_matrix(q1_values, field="q1_values", users=users)
    o2 = _score_matrix(o2_values, field="o2_values", users=users)
    o3 = _score_matrix(o3_values, field="o3_values", users=users)
    selected = np.full(users, NO_OP_ACTION, dtype=np.int64)
    eligible = np.any(raw_mask, axis=1)
    selected[eligible] = np.argmax(
        np.where(raw_mask[eligible], q1[eligible] + o2[eligible] + o3[eligible], -np.inf),
        axis=1,
    )
    return selected


@dataclass(frozen=True)
class JointC3Provenance:
    """Immutable, method-local construction metadata (no experiment identity)."""

    method: Literal["FOCAL_ROW", "M1D", "EXACT_O1", "AP_MONE"]
    interval_s: float
    lambda_bits_per_j: float
    kappa_bits: float
    user_order: np.ndarray
    max_sweeps: int = 0
    schema: str = JOINT_C3_SCHEMA

    def __post_init__(self) -> None:
        if self.method not in {"FOCAL_ROW", "M1D", "EXACT_O1", "AP_MONE"}:
            raise JointC3Error("provenance method is unknown")
        for field in ("interval_s", "lambda_bits_per_j", "kappa_bits"):
            object.__setattr__(self, field, _finite_positive(getattr(self, field), field=field))
        order = np.asarray(self.user_order)
        if (
            order.ndim != 1
            or not np.issubdtype(order.dtype, np.integer)
            or np.issubdtype(order.dtype, np.bool_)
            or sorted(int(value) for value in order.tolist()) != list(range(order.size))
        ):
            raise JointC3Error("user_order must be a permutation of its row indices")
        if type(self.max_sweeps) is not int or self.max_sweeps < 0:
            raise JointC3Error("max_sweeps must be a nonnegative integer")
        if self.schema != JOINT_C3_SCHEMA:
            raise JointC3Error("joint C3 schema is stale")
        object.__setattr__(self, "user_order", _readonly(order, dtype=np.int64))


@dataclass(frozen=True)
class JointC3Row:
    """Exact O1/O3 row for one focal replacement against a joint background."""

    reference_joint_actions: np.ndarray
    focal_user: int
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
    provenance: JointC3Provenance
    schema: str = JOINT_C3_SCHEMA

    def __post_init__(self) -> None:
        reference = np.asarray(self.reference_joint_actions)
        if reference.ndim != 1 or not np.issubdtype(reference.dtype, np.integer) or np.issubdtype(reference.dtype, np.bool_):
            raise JointC3Error("reference_joint_actions must be a one-dimensional integer vector")
        uid = int(self.focal_user)
        if uid < 0 or uid >= reference.size:
            raise JointC3Error("focal_user is outside reference_joint_actions")
        legal = np.asarray(self.legal_mask)
        if legal.dtype != np.bool_ or legal.shape != (NUM_ACTIONS,):
            raise JointC3Error("legal_mask must be Boolean shape (28,)")
        for field in (
            "focal_delta_bits", "nonfocal_delta_bits", "network_delta_energy_j", "z1_bits",
            "z3_bits", "system_surplus_bits", "identity_residual_bits", "q1_values", "q3_values",
        ):
            values = np.asarray(getattr(self, field), dtype=np.float64)
            if values.shape != (NUM_ACTIONS,) or not np.all(np.isfinite(values)):
                raise JointC3Error(f"{field} must be finite shape (28,)")
            if np.any(values[~legal] != 0.0):
                raise JointC3Error(f"{field} must be zero outside the safe mask")
            object.__setattr__(self, field, _readonly(values, dtype=np.float64))
        reference_action = int(reference[uid])
        if bool(np.any(legal)):
            if not 0 <= reference_action < NUM_ACTIONS or not bool(legal[reference_action]):
                raise JointC3Error("focal reference action must be legal")
            for field in (
                self.focal_delta_bits, self.nonfocal_delta_bits, self.network_delta_energy_j,
                self.z1_bits, self.z3_bits, self.system_surplus_bits, self.identity_residual_bits,
                self.q1_values, self.q3_values,
            ):
                if float(field[reference_action]) != 0.0:
                    raise JointC3Error("focal reference entry must be exact zero")
        elif reference_action != NO_OP_ACTION:
            raise JointC3Error("empty focal row requires no-op reference")
        magnitude = np.maximum(1.0, np.abs(self.z1_bits) + np.abs(self.z3_bits))
        tolerance = 512.0 * np.finfo(np.float64).eps * magnitude
        if np.any(np.abs(self.identity_residual_bits) > tolerance):
            raise JointC3Error("focal O1+O3 identity lost precision")
        if self.schema != JOINT_C3_SCHEMA:
            raise JointC3Error("joint C3 row schema is stale")
        object.__setattr__(self, "reference_joint_actions", _readonly(reference, dtype=np.int64))
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))


def build_focal_joint_c3_row(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    reference_joint_actions: object,
    focal_user: int,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
) -> JointC3Row:
    """Evaluate all legal replacements for one user against one joint vector."""

    _assert_anchor(environment, observation)
    if not isinstance(rng, np.random.Generator):
        raise JointC3Error("rng must be numpy.random.Generator")
    interval = _finite_positive(interval_s, field="interval_s")
    multiplier = _finite_positive(lambda_bits_per_j, field="lambda_bits_per_j")
    kappa = _finite_positive(kappa_bits, field="kappa_bits")
    reference = _safe_actions(observation, reference_joint_actions, field="reference_joint_actions")
    uid = int(focal_user)
    if uid < 0 or uid >= observation.num_users:
        raise JointC3Error("focal_user is outside the sealed anchor")
    legal = np.asarray(observation.masks[uid], dtype=np.bool_)
    shape = (NUM_ACTIONS,)
    focal_bits = np.zeros(shape, dtype=np.float64)
    nonfocal_bits = np.zeros(shape, dtype=np.float64)
    energy = np.zeros(shape, dtype=np.float64)
    z1 = np.zeros(shape, dtype=np.float64)
    z3 = np.zeros(shape, dtype=np.float64)
    total = np.zeros(shape, dtype=np.float64)
    reference_evaluation = environment.evaluate_actions(reference, rng)
    reference_rates = np.asarray(reference_evaluation.link_rate_bps, dtype=np.float64)
    reference_power = float(reference_evaluation.system_power_w)
    reference_action = int(reference[uid])
    for action in np.flatnonzero(legal).tolist():
        action = int(action)
        if action == reference_action:
            continue
        candidate = np.array(reference, copy=True)
        candidate[uid] = action
        evaluation = environment.evaluate_actions(candidate, rng)
        rates = np.asarray(evaluation.link_rate_bps, dtype=np.float64)
        delta = rates - reference_rates
        focal_bits[action] = interval * float(delta[uid])
        nonfocal_bits[action] = interval * math.fsum(float(delta[v]) for v in range(reference.size) if v != uid)
        energy[action] = interval * (float(evaluation.system_power_w) - reference_power)
        z1[action] = focal_bits[action] - multiplier * energy[action]
        z3[action] = nonfocal_bits[action]
        total[action] = interval * math.fsum(float(value) for value in delta) - multiplier * energy[action]
    return JointC3Row(
        reference_joint_actions=reference,
        focal_user=uid,
        legal_mask=legal,
        focal_delta_bits=focal_bits,
        nonfocal_delta_bits=nonfocal_bits,
        network_delta_energy_j=energy,
        z1_bits=z1,
        z3_bits=z3,
        system_surplus_bits=total,
        identity_residual_bits=z1 + z3 - total,
        q1_values=z1 / kappa,
        q3_values=z3 / kappa,
        provenance=JointC3Provenance("FOCAL_ROW", interval, multiplier, kappa, np.arange(reference.size)),
    )


@dataclass(frozen=True)
class M1DResult:
    """Outcome of the bounded Gauss--Seidel self-consistency construction."""

    status: Literal["CONVERGED", "FAIL_M1D_CYCLE", "FAIL_M1D_MAX_SWEEPS", "FAIL_M1D_ONE_PASS_EQUIVALENCE"]
    initial_actions: np.ndarray
    final_iterate_actions: np.ndarray
    production_actions: np.ndarray
    sweep_count: int
    changed_per_sweep: np.ndarray
    surfaces: MatchedOpeningSurfaces | None
    provenance: JointC3Provenance
    schema: str = JOINT_C3_SCHEMA

    def __post_init__(self) -> None:
        initial = np.asarray(self.initial_actions)
        final = np.asarray(self.final_iterate_actions)
        production = np.asarray(self.production_actions)
        for field, values in (("initial_actions", initial), ("final_iterate_actions", final), ("production_actions", production)):
            if values.shape != initial.shape or values.ndim != 1 or not np.issubdtype(values.dtype, np.integer):
                raise JointC3Error(f"{field} must be an integer user vector")
            object.__setattr__(self, field, _readonly(values, dtype=np.int64))
        changes = np.asarray(self.changed_per_sweep)
        if changes.ndim != 1 or not np.issubdtype(changes.dtype, np.integer) or np.any(changes < 0):
            raise JointC3Error("changed_per_sweep must be a nonnegative integer vector")
        if type(self.sweep_count) is not int or self.sweep_count != changes.size:
            raise JointC3Error("sweep_count must equal changed_per_sweep length")
        if self.status == "CONVERGED":
            if self.surfaces is None or not np.array_equal(final, production):
                raise JointC3Error("converged M1D needs exact one-pass-equivalent actions")
        elif self.surfaces is not None:
            raise JointC3Error("failed M1D must not expose executable surfaces")
        if self.schema != JOINT_C3_SCHEMA:
            raise JointC3Error("M1D schema is stale")
        object.__setattr__(self, "changed_per_sweep", _readonly(changes, dtype=np.int64))

    @property
    def converged(self) -> bool:
        return self.status == "CONVERGED"


def solve_m1d_joint_c3(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    initial_actions: object,
    q1_values: object,
    o2_values: object,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
    max_sweeps: int = 5,
) -> M1DResult:
    """Run fixed-order, bounded M1-D and require its final one-pass equality."""

    _assert_anchor(environment, observation)
    if type(max_sweeps) is not int or max_sweeps < 1 or max_sweeps > 5:
        raise JointC3Error("max_sweeps must be an integer in 1..5")
    reference = _safe_actions(observation, initial_actions, field="initial_actions")
    users = observation.num_users
    q1 = _score_matrix(q1_values, field="q1_values", users=users)
    o2 = _score_matrix(o2_values, field="o2_values", users=users)
    legal = np.asarray(observation.masks, dtype=np.bool_)
    interval = _finite_positive(interval_s, field="interval_s")
    multiplier = _finite_positive(lambda_bits_per_j, field="lambda_bits_per_j")
    kappa = _finite_positive(kappa_bits, field="kappa_bits")
    provenance = JointC3Provenance("M1D", interval, multiplier, kappa, np.arange(users), max_sweeps)
    current = np.array(reference, copy=True)
    seen = {tuple(int(value) for value in current.tolist())}
    changed: list[int] = []
    for sweep in range(1, max_sweeps + 1):
        changes = 0
        for uid in range(users):
            if not bool(np.any(legal[uid])):
                continue
            row = build_focal_joint_c3_row(
                environment, observation=observation, reference_joint_actions=current,
                focal_user=uid, rng=rng, lambda_bits_per_j=multiplier,
                interval_s=interval, kappa_bits=kappa,
            )
            candidate = int(np.argmax(np.where(legal[uid], q1[uid] + o2[uid] + row.q3_values, -np.inf)))
            if candidate != int(current[uid]):
                current[uid] = candidate
                changes += 1
        changed.append(changes)
        if changes == 0:
            surfaces = build_matched_opening_surfaces(
                environment, observation=observation, reference_joint_actions=current, rng=rng,
                lambda_bits_per_j=multiplier, interval_s=interval, kappa_bits=kappa,
            )
            production = select_masked_actions(q1, o2, surfaces.q3_values, legal)
            status: Literal["CONVERGED", "FAIL_M1D_ONE_PASS_EQUIVALENCE"] = (
                "CONVERGED" if np.array_equal(production, current) else "FAIL_M1D_ONE_PASS_EQUIVALENCE"
            )
            return M1DResult(
                status=status, initial_actions=reference, final_iterate_actions=current,
                production_actions=production, sweep_count=sweep,
                changed_per_sweep=np.asarray(changed, dtype=np.int64),
                surfaces=surfaces if status == "CONVERGED" else None, provenance=provenance,
            )
        vector = tuple(int(value) for value in current.tolist())
        if vector in seen:
            return M1DResult(
                status="FAIL_M1D_CYCLE", initial_actions=reference, final_iterate_actions=current,
                production_actions=np.full(users, NO_OP_ACTION, dtype=np.int64), sweep_count=sweep,
                changed_per_sweep=np.asarray(changed, dtype=np.int64), surfaces=None, provenance=provenance,
            )
        seen.add(vector)
    return M1DResult(
        status="FAIL_M1D_MAX_SWEEPS", initial_actions=reference, final_iterate_actions=current,
        production_actions=np.full(users, NO_OP_ACTION, dtype=np.int64), sweep_count=max_sweeps,
        changed_per_sweep=np.asarray(changed, dtype=np.int64), surfaces=None, provenance=provenance,
    )


@dataclass(frozen=True)
class ExactO1Result:
    """Bounded exact-O1 diagnostic solve, never a deployed policy result.

    ``coordinate_objective_deltas`` records the change made at each visited
    nonempty row.  For ``include_c3=True`` that is the exact fixed-lambda
    opening surplus divided by kappa plus the separable O2-score difference.
    It must not be negative beyond floating precision.
    """

    status: Literal[
        "CONVERGED", "FAIL_EXACT_O1_CYCLE", "FAIL_EXACT_O1_MAX_SWEEPS",
        "FAIL_EXACT_O1_ONE_PASS_EQUIVALENCE", "FAIL_EXACT_O1_MONOTONICITY",
    ]
    include_c3: bool
    initial_actions: np.ndarray
    final_iterate_actions: np.ndarray
    production_actions: np.ndarray
    sweep_count: int
    changed_per_sweep: np.ndarray
    coordinate_objective_deltas: np.ndarray
    monotonicity_violations: np.ndarray
    surfaces: MatchedOpeningSurfaces | None
    provenance: JointC3Provenance
    schema: str = JOINT_C3_SCHEMA

    def __post_init__(self) -> None:
        if type(self.include_c3) is not bool:
            raise JointC3Error("include_c3 must be Boolean")
        initial = np.asarray(self.initial_actions)
        final = np.asarray(self.final_iterate_actions)
        production = np.asarray(self.production_actions)
        for field, values in (("initial_actions", initial), ("final_iterate_actions", final), ("production_actions", production)):
            if values.shape != initial.shape or values.ndim != 1 or not np.issubdtype(values.dtype, np.integer):
                raise JointC3Error(f"{field} must be an integer user vector")
            object.__setattr__(self, field, _readonly(values, dtype=np.int64))
        changes = np.asarray(self.changed_per_sweep)
        if changes.ndim != 1 or not np.issubdtype(changes.dtype, np.integer) or np.any(changes < 0):
            raise JointC3Error("changed_per_sweep must be a nonnegative integer vector")
        if type(self.sweep_count) is not int or self.sweep_count != changes.size:
            raise JointC3Error("sweep_count must equal changed_per_sweep length")
        deltas = np.asarray(self.coordinate_objective_deltas, dtype=np.float64)
        if deltas.ndim != 1 or not np.all(np.isfinite(deltas)):
            raise JointC3Error("coordinate_objective_deltas must be a finite vector")
        violations = np.asarray(self.monotonicity_violations)
        if violations.ndim != 1 or violations.dtype != np.bool_ or violations.shape != deltas.shape:
            raise JointC3Error("monotonicity_violations must be Boolean and align with deltas")
        if self.include_c3 and bool(np.any(violations)) and self.status != "FAIL_EXACT_O1_MONOTONICITY":
            raise JointC3Error("full exact-O1 monotonicity violation cannot be accepted")
        if self.status == "CONVERGED":
            if self.surfaces is None or not np.array_equal(final, production):
                raise JointC3Error("converged exact-O1 needs exact one-pass-equivalent actions")
        elif self.surfaces is not None:
            raise JointC3Error("failed exact-O1 must not expose executable surfaces")
        if self.schema != JOINT_C3_SCHEMA:
            raise JointC3Error("exact-O1 schema is stale")
        object.__setattr__(self, "changed_per_sweep", _readonly(changes, dtype=np.int64))
        object.__setattr__(self, "coordinate_objective_deltas", _readonly(deltas, dtype=np.float64))
        object.__setattr__(self, "monotonicity_violations", _readonly(violations, dtype=np.bool_))

    @property
    def converged(self) -> bool:
        return self.status == "CONVERGED"


def solve_exact_o1_joint_c3(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    initial_actions: object,
    o2_values: object,
    include_c3: bool,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
    max_sweeps: int = 5,
) -> ExactO1Result:
    """Solve the nonbinding DIAG-O-DROP or DIAG-O-FULL construction.

    Every coordinate score uses a newly evaluated exact focal O1 row.  If
    ``include_c3`` is true, the same row supplies exact O3 and the routine
    receipts the stipulated non-decrease of fixed-lambda opening surplus plus
    the separable O2 score at every coordinate update.
    """

    _assert_anchor(environment, observation)
    if type(include_c3) is not bool:
        raise JointC3Error("include_c3 must be Boolean")
    if type(max_sweeps) is not int or max_sweeps < 1 or max_sweeps > 5:
        raise JointC3Error("max_sweeps must be an integer in 1..5")
    reference = _safe_actions(observation, initial_actions, field="initial_actions")
    users = observation.num_users
    o2 = _score_matrix(o2_values, field="o2_values", users=users)
    legal = np.asarray(observation.masks, dtype=np.bool_)
    interval = _finite_positive(interval_s, field="interval_s")
    multiplier = _finite_positive(lambda_bits_per_j, field="lambda_bits_per_j")
    kappa = _finite_positive(kappa_bits, field="kappa_bits")
    provenance = JointC3Provenance("EXACT_O1", interval, multiplier, kappa, np.arange(users), max_sweeps)
    current = np.array(reference, copy=True)
    seen = {tuple(int(value) for value in current.tolist())}
    changed: list[int] = []
    objective_deltas: list[float] = []
    violations: list[bool] = []
    for sweep in range(1, max_sweeps + 1):
        changes = 0
        for uid in range(users):
            if not bool(np.any(legal[uid])):
                continue
            row = build_focal_joint_c3_row(
                environment, observation=observation, reference_joint_actions=current,
                focal_user=uid, rng=rng, lambda_bits_per_j=multiplier,
                interval_s=interval, kappa_bits=kappa,
            )
            exact = row.q1_values + (row.q3_values if include_c3 else 0.0)
            candidate = int(np.argmax(np.where(legal[uid], exact + o2[uid], -np.inf)))
            prior = int(current[uid])
            # q1+q3 equals the exact fixed-lambda opening surplus/kappa.
            delta = float(exact[candidate] + o2[uid, candidate] - o2[uid, prior])
            tolerance = 1024.0 * np.finfo(np.float64).eps * max(
                1.0, abs(float(exact[candidate])), abs(float(o2[uid, candidate])), abs(float(o2[uid, prior]))
            )
            violated = bool(include_c3 and delta < -tolerance)
            objective_deltas.append(delta)
            violations.append(violated)
            if violated:
                return ExactO1Result(
                    status="FAIL_EXACT_O1_MONOTONICITY", include_c3=include_c3,
                    initial_actions=reference, final_iterate_actions=current,
                    production_actions=np.full(users, NO_OP_ACTION, dtype=np.int64), sweep_count=sweep,
                    changed_per_sweep=np.asarray(changed + [changes], dtype=np.int64),
                    coordinate_objective_deltas=np.asarray(objective_deltas, dtype=np.float64),
                    monotonicity_violations=np.asarray(violations, dtype=np.bool_), surfaces=None,
                    provenance=provenance,
                )
            if candidate != prior:
                current[uid] = candidate
                changes += 1
        changed.append(changes)
        if changes == 0:
            surfaces = build_matched_opening_surfaces(
                environment, observation=observation, reference_joint_actions=current, rng=rng,
                lambda_bits_per_j=multiplier, interval_s=interval, kappa_bits=kappa,
            )
            exact_full = surfaces.q1_values + (surfaces.q3_values if include_c3 else 0.0)
            production = select_masked_actions(exact_full, o2, np.zeros_like(exact_full), legal)
            status: Literal["CONVERGED", "FAIL_EXACT_O1_ONE_PASS_EQUIVALENCE"] = (
                "CONVERGED" if np.array_equal(production, current) else "FAIL_EXACT_O1_ONE_PASS_EQUIVALENCE"
            )
            return ExactO1Result(
                status=status, include_c3=include_c3, initial_actions=reference,
                final_iterate_actions=current, production_actions=production, sweep_count=sweep,
                changed_per_sweep=np.asarray(changed, dtype=np.int64),
                coordinate_objective_deltas=np.asarray(objective_deltas, dtype=np.float64),
                monotonicity_violations=np.asarray(violations, dtype=np.bool_),
                surfaces=surfaces if status == "CONVERGED" else None, provenance=provenance,
            )
        vector = tuple(int(value) for value in current.tolist())
        if vector in seen:
            return ExactO1Result(
                status="FAIL_EXACT_O1_CYCLE", include_c3=include_c3, initial_actions=reference,
                final_iterate_actions=current, production_actions=np.full(users, NO_OP_ACTION, dtype=np.int64),
                sweep_count=sweep, changed_per_sweep=np.asarray(changed, dtype=np.int64),
                coordinate_objective_deltas=np.asarray(objective_deltas, dtype=np.float64),
                monotonicity_violations=np.asarray(violations, dtype=np.bool_), surfaces=None, provenance=provenance,
            )
        seen.add(vector)
    return ExactO1Result(
        status="FAIL_EXACT_O1_MAX_SWEEPS", include_c3=include_c3, initial_actions=reference,
        final_iterate_actions=current, production_actions=np.full(users, NO_OP_ACTION, dtype=np.int64),
        sweep_count=max_sweeps, changed_per_sweep=np.asarray(changed, dtype=np.int64),
        coordinate_objective_deltas=np.asarray(objective_deltas, dtype=np.float64),
        monotonicity_violations=np.asarray(violations, dtype=np.bool_), surfaces=None, provenance=provenance,
    )


def _joint_surplus(
    environment: StepEnvironment, actions: np.ndarray, reference: np.ndarray, rng: np.random.Generator,
    *, interval_s: float, lambda_bits_per_j: float,
) -> float:
    evaluation = environment.evaluate_actions(actions, rng)
    baseline = environment.evaluate_actions(reference, rng)
    rate_delta = np.asarray(evaluation.link_rate_bps, dtype=np.float64) - np.asarray(baseline.link_rate_bps, dtype=np.float64)
    energy = float(evaluation.system_power_w) - float(baseline.system_power_w)
    return float(interval_s * math.fsum(float(value) for value in rate_delta) - lambda_bits_per_j * interval_s * energy)


@dataclass(frozen=True)
class AntitheticPermutationSurface:
    """AP-MONE O1/O3 surface plus exact two-order telescoping receipts."""

    reference_actions: np.ndarray
    proposal_actions: np.ndarray
    permutation: np.ndarray
    legal_mask: np.ndarray
    z1_bits: np.ndarray
    z3_bits: np.ndarray
    q1_values: np.ndarray
    q3_values: np.ndarray
    order_credited_z1_bits: np.ndarray
    order_credited_z3_bits: np.ndarray
    order_credited_sum_bits: np.ndarray
    order_joint_surplus_bits: np.ndarray
    order_identity_residual_bits: np.ndarray
    provenance: JointC3Provenance
    schema: str = JOINT_C3_SCHEMA

    def __post_init__(self) -> None:
        reference = np.asarray(self.reference_actions)
        proposal = np.asarray(self.proposal_actions)
        if reference.ndim != 1 or proposal.shape != reference.shape or not np.issubdtype(reference.dtype, np.integer) or not np.issubdtype(proposal.dtype, np.integer):
            raise JointC3Error("reference_actions and proposal_actions must be aligned integer user vectors")
        users = reference.size
        legal = np.asarray(self.legal_mask)
        if legal.dtype != np.bool_ or legal.shape != (users, NUM_ACTIONS):
            raise JointC3Error("legal_mask must be Boolean shape (users, 28)")
        permutation = np.asarray(self.permutation)
        if permutation.shape != (users,) or not np.issubdtype(permutation.dtype, np.integer) or sorted(int(value) for value in permutation.tolist()) != list(range(users)):
            raise JointC3Error("permutation must be a complete user permutation")
        for field in ("z1_bits", "z3_bits", "q1_values", "q3_values"):
            values = np.asarray(getattr(self, field), dtype=np.float64)
            if values.shape != (users, NUM_ACTIONS) or not np.all(np.isfinite(values)) or np.any(values[~legal] != 0.0):
                raise JointC3Error(f"{field} must be finite (users, 28) and zero outside mask")
            object.__setattr__(self, field, _readonly(values, dtype=np.float64))
        for field in ("order_credited_z1_bits", "order_credited_z3_bits"):
            values = np.asarray(getattr(self, field), dtype=np.float64)
            if values.shape != (2, users) or not np.all(np.isfinite(values)):
                raise JointC3Error(f"{field} must be finite shape (2, users)")
            object.__setattr__(self, field, _readonly(values, dtype=np.float64))
        for field in ("order_credited_sum_bits", "order_joint_surplus_bits", "order_identity_residual_bits"):
            values = np.asarray(getattr(self, field), dtype=np.float64)
            if values.shape != (2,) or not np.all(np.isfinite(values)):
                raise JointC3Error(f"{field} must be finite shape (2,)")
            object.__setattr__(self, field, _readonly(values, dtype=np.float64))
        for uid, action in enumerate(reference.tolist()):
            if bool(np.any(legal[uid])):
                if not bool(legal[uid, int(action)]) or not bool(legal[uid, int(proposal[uid])]):
                    raise JointC3Error("reference/proposal action must be legal for every nonempty row")
                if any(float(field[uid, int(action)]) != 0.0 for field in (self.z1_bits, self.z3_bits, self.q1_values, self.q3_values)):
                    raise JointC3Error("AP reference surface entries must be exact zero")
            elif int(action) != NO_OP_ACTION or int(proposal[uid]) != NO_OP_ACTION:
                raise JointC3Error("empty rows require no-op reference and proposal")
        magnitude = np.maximum(1.0, np.abs(self.order_credited_sum_bits) + np.abs(self.order_joint_surplus_bits))
        if np.any(np.abs(self.order_identity_residual_bits) > 1024.0 * np.finfo(np.float64).eps * magnitude):
            raise JointC3Error("AP telescoping identity lost precision")
        if self.schema != JOINT_C3_SCHEMA:
            raise JointC3Error("AP surface schema is stale")
        object.__setattr__(self, "reference_actions", _readonly(reference, dtype=np.int64))
        object.__setattr__(self, "proposal_actions", _readonly(proposal, dtype=np.int64))
        object.__setattr__(self, "permutation", _readonly(permutation, dtype=np.int64))
        object.__setattr__(self, "legal_mask", _readonly(legal, dtype=np.bool_))


def build_ap_mone_surface(
    environment: StepEnvironment,
    *,
    observation: StepObservation,
    reference_actions: object,
    q1_values: object,
    o2_values: object,
    permutation: object,
    rng: np.random.Generator,
    lambda_bits_per_j: float,
    interval_s: float = OPS3_INTERVAL_S,
    kappa_bits: float = OPS3_KAPPA_BITS,
) -> AntitheticPermutationSurface:
    """Build AP-MONE around ``reference_actions`` using a supplied keyed order."""

    _assert_anchor(environment, observation)
    if not isinstance(rng, np.random.Generator):
        raise JointC3Error("rng must be numpy.random.Generator")
    reference = _safe_actions(observation, reference_actions, field="reference_actions")
    users = observation.num_users
    q1 = _score_matrix(q1_values, field="q1_values", users=users)
    o2 = _score_matrix(o2_values, field="o2_values", users=users)
    legal = np.asarray(observation.masks, dtype=np.bool_)
    order = np.asarray(permutation)
    if order.shape != (users,) or not np.issubdtype(order.dtype, np.integer) or np.issubdtype(order.dtype, np.bool_) or sorted(int(value) for value in order.tolist()) != list(range(users)):
        raise JointC3Error("permutation must be a complete integer user permutation")
    interval = _finite_positive(interval_s, field="interval_s")
    multiplier = _finite_positive(lambda_bits_per_j, field="lambda_bits_per_j")
    kappa = _finite_positive(kappa_bits, field="kappa_bits")
    base = build_matched_opening_surfaces(
        environment, observation=observation, reference_joint_actions=reference, rng=rng,
        lambda_bits_per_j=multiplier, interval_s=interval, kappa_bits=kappa,
    )
    proposal = select_masked_actions(q1, o2, base.q3_values, legal)
    z1_acc = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    z3_acc = np.zeros((users, NUM_ACTIONS), dtype=np.float64)
    credited_z1 = np.zeros((2, users), dtype=np.float64)
    credited_z3 = np.zeros((2, users), dtype=np.float64)
    orders = (np.array(order, copy=True), np.array(order[::-1], copy=True))
    for index, ordered_users in enumerate(orders):
        current = np.array(reference, copy=True)
        for uid_raw in ordered_users.tolist():
            uid = int(uid_raw)
            # current already has predecessors at p and this/successors at b0.
            row = build_focal_joint_c3_row(
                environment, observation=observation, reference_joint_actions=current,
                focal_user=uid, rng=rng, lambda_bits_per_j=multiplier,
                interval_s=interval, kappa_bits=kappa,
            )
            z1_acc[uid] += row.z1_bits / 2.0
            z3_acc[uid] += row.z3_bits / 2.0
            action = int(proposal[uid])
            credited_z1[index, uid] = float(row.z1_bits[action])
            credited_z3[index, uid] = float(row.z3_bits[action])
            current[uid] = action
        if not np.array_equal(current, proposal):
            raise JointC3Error("AP construction did not reach the fixed proposal")
    credited_sum = np.sum(credited_z1 + credited_z3, axis=1, dtype=np.float64)
    joint = np.asarray([
        _joint_surplus(environment, proposal, reference, rng, interval_s=interval, lambda_bits_per_j=multiplier),
        _joint_surplus(environment, proposal, reference, rng, interval_s=interval, lambda_bits_per_j=multiplier),
    ], dtype=np.float64)
    return AntitheticPermutationSurface(
        reference_actions=reference, proposal_actions=proposal, permutation=order,
        legal_mask=legal, z1_bits=z1_acc, z3_bits=z3_acc, q1_values=z1_acc / kappa,
        q3_values=z3_acc / kappa, order_credited_z1_bits=credited_z1,
        order_credited_z3_bits=credited_z3, order_credited_sum_bits=credited_sum,
        order_joint_surplus_bits=joint, order_identity_residual_bits=credited_sum - joint,
        provenance=JointC3Provenance("AP_MONE", interval, multiplier, kappa, order),
    )


__all__ = [
    "JOINT_C3_SCHEMA", "JointC3Error", "JointC3Provenance", "JointC3Row",
    "M1DResult", "ExactO1Result", "AntitheticPermutationSurface", "select_masked_actions",
    "build_focal_joint_c3_row", "solve_m1d_joint_c3", "solve_exact_o1_joint_c3",
    "build_ap_mone_surface",
]
