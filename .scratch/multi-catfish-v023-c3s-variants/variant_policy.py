#!/usr/bin/env python3
"""Single-change C3-S policy variants built on the immutable v1 policy seam."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from fractions import Fraction
import json
import math
from pathlib import Path
import resource
import sys
import time
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
V1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3s-screen"
if str(V1_DIR) not in sys.path:
    sys.path.insert(0, str(V1_DIR))

import c3s_policy as v1  # noqa: E402
from mcrl.runtime.ee_axis_ops3_live import (  # noqa: E402
    build_ops3_live_surfaces,
    project_ops3_anchor,
    snapshot_ops3_anchor,
)


CONFIG_PATH = HERE / "variants_config.json"
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-c3s-variant-matrix-config-v1"
VARIANT_ARMS = ("LITE", "V-J", "V-U", "V-M", "V-C", "V-H", "V-P", "V-L2")


class VariantPolicyError(v1.C3SPolicyError):
    """A variant constant, projection, hook, or state transition failed closed."""


def _fraction(value: object, *, field_name: str) -> Fraction:
    try:
        if isinstance(value, Mapping):
            result = Fraction(int(value["numerator"]), int(value["denominator"]))
        else:
            result = Fraction(str(value))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise VariantPolicyError(f"{field_name} is not an exact rational") from error
    if result < 0:
        raise VariantPolicyError(f"{field_name} must be nonnegative")
    return result


def load_constants(path: Path = CONFIG_PATH) -> dict[str, object]:
    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VariantPolicyError("variant config is absent or malformed") from error
    if not isinstance(payload, dict) or set(payload) != {"schema", "constants", "imports"}:
        raise VariantPolicyError("variant config top-level schema drifted")
    constants = payload.get("constants")
    if payload.get("schema") != CONFIG_SCHEMA or not isinstance(constants, dict):
        raise VariantPolicyError("variant config schema drifted")
    expected = {
        "arms", "worlds", "lineages", "horizon_steps", "users", "service_margin",
        "latency_threshold_seconds", "association_reversal_window_steps",
        "V-J.catalog", "V-U.catalog",
        "V-U.top_actions_per_user", "V-M.catalog",
        "V-M.acceptance_margin_base_bits_fraction", "V-C.catalog",
        "V-C.cadence_steps", "V-C.cadence_residue", "V-H.catalog",
        "V-H.exclusion_steps", "V-P.catalog", "V-P.projection_horizon_cap",
        "V-P.persistence_kappa_bits", "V-P.persistence_indicator",
        "V-L2.catalog", "V-L2.lookahead_steps", "V-L2.projection_channels",
        "V-L2.objective_intervals",
    }
    if set(constants) != expected:
        raise VariantPolicyError("variant constants are incomplete or contain undeclared levers")
    if tuple(constants["arms"]) != ("BASE", *VARIANT_ARMS):
        raise VariantPolicyError("arm order drifted")
    if constants["V-J.catalog"] != "EVACUATION_ONLY":
        raise VariantPolicyError("V-J catalog constant drifted")
    if (
        constants["V-U.catalog"] != "UNILATERAL_ONLY_TOP_2_PER_USER"
        or constants["V-U.top_actions_per_user"] != 2
        or constants["V-M.catalog"] != "LITE"
        or constants["V-C.catalog"] != "LITE"
        or constants["V-H.catalog"] != "LITE"
        or constants["V-P.catalog"] != "LITE"
        or constants["V-L2.catalog"] != "LITE"
        or constants["V-C.cadence_steps"] != 3
        or constants["V-C.cadence_residue"] != 0
        or constants["V-H.exclusion_steps"] != 3
        or constants["V-P.projection_horizon_cap"] != 3
        or constants["V-P.persistence_indicator"] != "ABSORBING_FINAL_OFFSET"
        or constants["V-L2.lookahead_steps"] != 1
        or constants["V-L2.projection_channels"] != "MEDIAN_NO_FADING"
        or constants["V-L2.objective_intervals"] != 2
        or constants["association_reversal_window_steps"] != 3
    ):
        raise VariantPolicyError("one or more variant lever constants drifted")
    _fraction(constants["service_margin"], field_name="service_margin")
    _fraction(constants["V-M.acceptance_margin_base_bits_fraction"], field_name="V-M margin")
    _fraction(constants["V-P.persistence_kappa_bits"], field_name="V-P kappa")
    _fraction(constants["latency_threshold_seconds"], field_name="latency threshold")
    return dict(constants)


def persistence_objective(
    metric: Mapping[str, object], *, eta_ref: Fraction,
    persistence: Sequence[float], kappa_bits: Fraction,
) -> Fraction:
    """Exact V-P arithmetic for a complete profile's final-offset indicators."""

    score = v1.nominal_score(metric, eta_ref)
    loss = Fraction(0)
    for value in persistence:
        indicator = Fraction.from_float(float(value))
        if indicator not in (Fraction(0), Fraction(1)):
            raise VariantPolicyError("projected persistence indicator must be binary")
        loss += 1 - indicator
    return score - kappa_bits * loss


def lookahead_objective(
    current: Mapping[str, object], future_base: Mapping[str, object], *, eta_ref: Fraction,
) -> Fraction:
    return v1.nominal_score(current, eta_ref) + v1.nominal_score(future_base, eta_ref)


def association_reversals(trace: Sequence[Sequence[tuple[int, int] | None]], *, window: int = 3) -> int:
    """Count user-level A→B→A reversals whose endpoints are at most ``window`` apart."""

    if not trace:
        return 0
    users = len(trace[0])
    if any(len(row) != users for row in trace):
        raise VariantPolicyError("association trace width drifted")
    total = 0
    for user in range(users):
        values = [row[user] for row in trace]
        for end in range(2, len(values)):
            start_floor = max(0, end - window)
            if values[end] is None:
                continue
            matched = False
            for middle in range(end - 1, start_floor, -1):
                if values[middle] is None or values[middle] == values[end]:
                    continue
                if any(values[start] == values[end] for start in range(start_floor, middle)):
                    matched = True
                    break
            total += int(matched)
    return total


@dataclass(frozen=True)
class DecisionContext:
    step_index: int
    ops3_surfaces: tuple[Any, ...] | None = None
    lookahead_environment: Any | None = field(default=None, repr=False, compare=False)


CatalogBuilder = Callable[[tuple[dict[str, object], ...], Any, "VariantPolicyAdapter"], tuple[dict[str, object], ...]]
Objective = Callable[[Mapping[str, object], DecisionContext, "VariantPolicyAdapter"], Fraction]
Gate = Callable[[Mapping[str, object], Mapping[str, object], DecisionContext, "VariantPolicyAdapter"], bool]
PostDecision = Callable[[Mapping[str, object], Mapping[str, object], DecisionContext, "VariantPolicyAdapter"], None]


@dataclass(frozen=True)
class VariantHooks:
    catalog_builder: CatalogBuilder
    objective: Objective
    gate: Gate
    post_decision_state: PostDecision


def _identity_catalog(
    rows: tuple[dict[str, object], ...], _snapshot: Any, _adapter: "VariantPolicyAdapter",
) -> tuple[dict[str, object], ...]:
    return rows


def _catalog_kind(kind: str) -> CatalogBuilder:
    def build(rows: tuple[dict[str, object], ...], _snapshot: Any, _adapter: "VariantPolicyAdapter") -> tuple[dict[str, object], ...]:
        return tuple(row for row in rows if row["kind"] in ("base", kind))
    return build


def _hysteresis_catalog(
    rows: tuple[dict[str, object], ...], snapshot: Any, adapter: "VariantPolicyAdapter",
) -> tuple[dict[str, object], ...]:
    blocked = {
        user for user, through in adapter.blocked_through.items()
        if adapter.decision_index <= through
    }
    base = np.asarray(snapshot.base_actions)
    return tuple(
        row for row in rows
        if row["kind"] == "base" or not any(
            int(np.asarray(row["actions"])[user]) != int(base[user]) for user in blocked
        )
    )


def _nominal_objective(row: Mapping[str, object], _context: DecisionContext, adapter: "VariantPolicyAdapter") -> Fraction:
    return v1.nominal_score(row["nominal"], adapter.eta_ref)  # type: ignore[arg-type]


def _persistence_objective(row: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter") -> Fraction:
    surfaces = context.ops3_surfaces
    if surfaces is None:
        raise VariantPolicyError("V-P lacks an OPS-3 projection")
    actions = np.asarray(row["actions"], dtype=np.int64)
    indicators = []
    for user, action in enumerate(actions.tolist()):
        surface = surfaces[user]
        indicators.append(
            1.0 if surface.horizon == 0
            else 0.0 if action < 0
            else float(surface.persistence[surface.horizon - 1, action])
        )
    return persistence_objective(
        row["nominal"], eta_ref=adapter.eta_ref, persistence=indicators,
        kappa_bits=adapter.kappa_bits,
    )  # type: ignore[arg-type]


def _metric_from_outcome(outcome: Any, interval_s: float) -> dict[str, object]:
    rates = np.asarray(outcome.link_rate_bps, dtype=np.float64)
    return {
        "total_bits": interval_s * math.fsum(float(value) for value in rates),
        "total_energy_j": interval_s * float(outcome.system_power_w),
        "served": int(outcome.resolution.served_count),
        "opportunities": int(rates.size),
    }


def _future_base_metric(
    row: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter",
) -> Mapping[str, object] | None:
    if context.lookahead_environment is None:
        return None
    clone = copy.deepcopy(context.lookahead_environment)
    clone.physics = replace(clone.physics, fading_enabled=False)
    clone._fading_field = None
    outcome = clone.step(np.asarray(row["actions"], dtype=np.int64), np.random.default_rng(0))
    if bool(outcome.done):
        return None
    projected_snapshot, projected_evaluator = v1._snapshot_inputs(adapter, clone, outcome.observation)
    evaluation = projected_evaluator.evaluate(projected_snapshot.base_actions)
    return _metric_from_outcome(evaluation, projected_snapshot.interval_s)


def _lookahead_objective(row: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter") -> Fraction:
    future = _future_base_metric(row, context, adapter)
    if future is None:
        return v1.nominal_score(row["nominal"], adapter.eta_ref)  # type: ignore[arg-type]
    return lookahead_objective(row["nominal"], future, eta_ref=adapter.eta_ref)  # type: ignore[arg-type]


def _always_gate(_selected: Mapping[str, object], _base: Mapping[str, object], _context: DecisionContext, _adapter: "VariantPolicyAdapter") -> bool:
    return True


def _margin_gate(selected: Mapping[str, object], base: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter") -> bool:
    improvement = adapter.hooks.objective(selected, context, adapter) - adapter.hooks.objective(base, context, adapter)
    base_bits = Fraction.from_float(float(base["nominal"]["total_bits"]))  # type: ignore[index]
    return improvement >= adapter.margin_fraction * base_bits


def _cadence_gate(_selected: Mapping[str, object], _base: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter") -> bool:
    return context.step_index % adapter.cadence_steps == adapter.cadence_residue


def _noop_post(_selected: Mapping[str, object], _base: Mapping[str, object], _context: DecisionContext, _adapter: "VariantPolicyAdapter") -> None:
    return None


def _hysteresis_post(selected: Mapping[str, object], base: Mapping[str, object], context: DecisionContext, adapter: "VariantPolicyAdapter") -> None:
    chosen = np.asarray(selected["actions"])
    reference = np.asarray(base["actions"])
    for user in np.flatnonzero(chosen != reference).tolist():
        adapter.blocked_through[int(user)] = context.step_index + adapter.hysteresis_steps


def hooks_for(arm: str) -> VariantHooks:
    if arm not in VARIANT_ARMS:
        raise VariantPolicyError(f"unknown coordinator arm: {arm}")
    catalog = _identity_catalog
    objective = _nominal_objective
    gate = _always_gate
    post = _noop_post
    if arm == "V-J":
        catalog = _catalog_kind("joint")
    elif arm == "V-U":
        catalog = _catalog_kind("unilateral")
    elif arm == "V-M":
        gate = _margin_gate
    elif arm == "V-C":
        gate = _cadence_gate
    elif arm == "V-H":
        catalog, post = _hysteresis_catalog, _hysteresis_post
    elif arm == "V-P":
        objective = _persistence_objective
    elif arm == "V-L2":
        objective = _lookahead_objective
    return VariantHooks(catalog, objective, gate, post)


def select_with_hooks(
    catalog: Sequence[Mapping[str, object]], *, context: DecisionContext,
    adapter: "VariantPolicyAdapter",
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, Fraction]]:
    if not catalog or catalog[0].get("profile_id") != "BASE":
        raise VariantPolicyError("variant catalog must begin with BASE")
    base = catalog[0]
    base_metric = v1._metric(base["nominal"], label="BASE nominal")  # type: ignore[arg-type]
    scores: dict[str, Fraction] = {}
    eligible: list[Mapping[str, object]] = []
    for row in catalog:
        metric = v1._metric(row["nominal"], label=str(row["profile_id"]))  # type: ignore[arg-type]
        if metric["opportunities"] != base_metric["opportunities"]:
            raise VariantPolicyError("variant opportunity count differs from BASE")
        if int(metric["served"]) >= int(base_metric["served"]):
            scores[str(row["profile_id"])] = adapter.hooks.objective(row, context, adapter)
            eligible.append(row)
    best_score = max(scores[str(row["profile_id"])] for row in eligible)
    selected = min(
        (row for row in eligible if scores[str(row["profile_id"])] == best_score),
        key=v1._tie_key,
    )
    if not adapter.hooks.gate(selected, base, context, adapter):
        selected = base
    adapter.hooks.post_decision_state(selected, base, context, adapter)
    return selected, base, scores


def _base_only_catalog(
    snapshot: Any, evaluator: Any, timing_out: dict[str, float],
) -> tuple[dict[str, object], ...]:
    """Evaluate only BASE for a cadence-off decision."""

    started = time.perf_counter()
    evaluation = evaluator.evaluate(snapshot.base_actions)
    profile, _link_power = v1.f1.profile_from_evaluation(
        evaluation, interval_s=snapshot.interval_s
    )
    nominal = v1._metric_from_e1_payload(
        v1.e1._profile_metrics(profile), label="BASE nominal evaluation"
    )
    elapsed = time.perf_counter() - started
    timing_out.update({
        "base_nominal_evaluation": elapsed,
        "enumeration": 0.0,
        "remaining_nominal_evaluations": 0.0,
        "nominal_evaluation": elapsed,
        "unique_nominal_evaluations": 1.0,
    })
    return ({
        "profile_id": "BASE", "kind": "base", "tie_key": (0,),
        "actions": np.asarray(snapshot.base_actions, dtype=np.int64).copy(),
        "nominal": nominal,
    },)


class VariantPolicyAdapter:
    """Generic variant adapter with catalog/objective/gate/post-state hooks."""

    def __init__(
        self, *, physical: Any, frozen: Any, arm: str,
        eta_ref: Fraction | None = None, constants_path: Path = CONFIG_PATH,
    ) -> None:
        self.physical = physical
        self.frozen = frozen
        self.arm = arm
        self.catalog = "lite"
        self.eta_ref = v1.load_eta_ref() if eta_ref is None else Fraction(eta_ref)
        self.constants = load_constants(constants_path)
        self.hooks = hooks_for(arm)
        self.margin_fraction = _fraction(
            self.constants["V-M.acceptance_margin_base_bits_fraction"], field_name="V-M margin"
        )
        self.kappa_bits = _fraction(self.constants["V-P.persistence_kappa_bits"], field_name="V-P kappa")
        self.cadence_steps = int(self.constants["V-C.cadence_steps"])
        self.cadence_residue = int(self.constants["V-C.cadence_residue"])
        self.hysteresis_steps = int(self.constants["V-H.exclusion_steps"])
        self.blocked_through: dict[int, int] = {}
        self.decision_index = 0
        self.decision_records: list[dict[str, object]] = []

    def _context(self, step_env: Any, observation: Any, snapshot: Any) -> DecisionContext:
        surfaces = None
        lookahead = None
        if self.arm == "V-P":
            anchor = snapshot_ops3_anchor(step_env, observation)
            if anchor.horizon > int(self.constants["V-P.projection_horizon_cap"]):
                raise VariantPolicyError("OPS-3 projection exceeded configured horizon")
            projection = project_ops3_anchor(anchor)
            surfaces = build_ops3_live_surfaces(anchor, projection, snapshot.base_actions)
        elif self.arm == "V-L2":
            lookahead = copy.deepcopy(step_env)
        return DecisionContext(
            step_index=int(observation.step_index), ops3_surfaces=surfaces,
            lookahead_environment=lookahead,
        )

    def select_actions(self, step_env: Any, observation: Any, rng: np.random.Generator) -> np.ndarray:
        if not isinstance(rng, np.random.Generator):
            raise VariantPolicyError("policy RNG must be numpy.random.Generator")
        before = v1._live_neutrality_fingerprint(step_env, rng)
        started = time.perf_counter()
        snapshot, evaluator = v1._snapshot_inputs(self, step_env, observation)
        context = self._context(step_env, observation, snapshot)
        phases: dict[str, float] = {"q_inference": snapshot.q_inference_seconds}
        catalog_started = time.perf_counter()
        cadence_off = (
            self.arm == "V-C"
            and context.step_index % self.cadence_steps != self.cadence_residue
        )
        base_catalog = (
            _base_only_catalog(snapshot, evaluator, phases)
            if cadence_off
            else v1.build_s0_catalog(snapshot=snapshot, evaluator=evaluator, timing_out=phases)
        )
        catalog = self.hooks.catalog_builder(base_catalog, snapshot, self)
        phases["catalog_total"] = time.perf_counter() - catalog_started
        unique = int(phases.pop("unique_nominal_evaluations"))
        selection_started = time.perf_counter()
        selected, base, scores = select_with_hooks(catalog, context=context, adapter=self)
        phases["selection"] = time.perf_counter() - selection_started
        elapsed = time.perf_counter() - started
        after = v1._live_neutrality_fingerprint(step_env, rng)
        if before != after:
            raise VariantPolicyError("variant decision mutated live environment/RNG/tracking state")
        actions = np.asarray(selected["actions"], dtype=np.int64)
        base_actions = np.asarray(base["actions"], dtype=np.int64)
        counts = {kind: sum(row["kind"] == kind for row in catalog) for kind in ("base", "unilateral", "joint")}
        self.decision_records.append({
            "decision_index": self.decision_index,
            "arm": self.arm,
            "wall_seconds_hex": elapsed.hex(),
            "catalog_size": len(catalog),
            "unique_nominal_evaluations": unique,
            "profile_counts": counts,
            "selected_profile_id": str(selected["profile_id"]),
            "selected_objective": v1.fraction_payload(scores[str(selected["profile_id"])]),
            "base_objective": v1.fraction_payload(scores["BASE"]),
            "action_changed": not np.array_equal(actions, base_actions),
            "phase_wall_seconds_hex": {name: float(value).hex() for name, value in phases.items()},
            "process_lifetime_peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        })
        self.decision_index += 1
        return actions.copy()


__all__ = [
    "CONFIG_PATH", "VARIANT_ARMS", "DecisionContext", "VariantHooks",
    "VariantPolicyAdapter", "VariantPolicyError", "association_reversals",
    "hooks_for", "load_constants", "lookahead_objective",
    "persistence_objective", "select_with_hooks",
]
