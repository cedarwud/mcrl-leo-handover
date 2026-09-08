#!/usr/bin/env python3
"""Deployable S0 set-level coordinator used by the C3S closed-loop screen."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import json
import math
from pathlib import Path
import resource
import sys
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
E1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-existence-e1"
F1_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f1"
F2_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-contingency-f2"
S0_DIR = REPO / ".scratch" / "multi-catfish-v023-c3-probe-s0"
for _path in (E1_DIR, F1_DIR, F2_DIR, S0_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import run_probe_s0 as s0  # noqa: E402
import run_v023_c3_existence_e1 as e1  # noqa: E402
import run_v023_c3_contingency_f1 as f1  # noqa: E402


CONFIG_PATH = HERE / "c3s_config.json"
CONFIG_SCHEMA = "multi-catfish-mcrl-v023-c3s-policy-config-v1"
NOMINAL_CONVENTION = "OPS3_UNIT_RICIAN_GAIN_ZERO_DB_SHADOW_CURRENT_ANCHOR_ONLY"


class C3SPolicyError(RuntimeError):
    """A policy input, donor rule, or evaluation-neutrality check failed."""


def fraction_payload(value: Fraction) -> dict[str, str]:
    return {
        "numerator": str(value.numerator),
        "denominator": str(value.denominator),
        "float_hex": float(value).hex(),
    }


def load_eta_ref(path: Path = CONFIG_PATH) -> Fraction:
    """Load the injected constant; this path never derives it from screen outcomes."""

    try:
        payload = json.loads(Path(path).read_text(encoding="ascii"))
        raw = payload["eta_ref"]
        value = Fraction(int(raw["numerator"]), int(raw["denominator"]))
        encoded = float.fromhex(raw["float_hex"])
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError,
            ValueError, ZeroDivisionError) as error:
        raise C3SPolicyError("eta_ref config is missing or malformed") from error
    if (
        not isinstance(payload, dict)
        or set(payload) != {"schema", "eta_ref", "source"}
        or payload.get("schema") != CONFIG_SCHEMA
        or not isinstance(raw, dict)
        or set(raw) != {"numerator", "denominator", "float_hex"}
        or value <= 0
        or not math.isfinite(encoded)
        or encoded.hex() != float(value).hex()
        or value != Fraction.from_float(encoded)
    ):
        raise C3SPolicyError("eta_ref config does not bind one positive exact constant")
    return value


def _metric(value: Mapping[str, object], *, label: str) -> dict[str, object]:
    try:
        bits = float(value["total_bits"])
        energy = float(value["total_energy_j"])
        served = value["served"]
        opportunities = value["opportunities"]
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        raise C3SPolicyError(f"{label} metric is malformed") from error
    if (
        not math.isfinite(bits) or bits < 0.0
        or not math.isfinite(energy) or energy <= 0.0
        or type(served) is not int or type(opportunities) is not int
        or opportunities <= 0 or not 0 <= served <= opportunities
    ):
        raise C3SPolicyError(f"{label} metric is outside its domain")
    return {
        "total_bits": bits,
        "total_energy_j": energy,
        "served": served,
        "opportunities": opportunities,
    }


def nominal_score(metric: Mapping[str, object], eta_ref: Fraction) -> Fraction:
    parsed = _metric(metric, label="nominal")
    return (
        Fraction.from_float(float(parsed["total_bits"]))
        - eta_ref * Fraction.from_float(float(parsed["total_energy_j"]))
    )


def _tie_key(row: Mapping[str, object]) -> tuple[int, ...]:
    profile_id = str(row.get("profile_id", ""))
    if profile_id == "BASE":
        return (0,)
    explicit = row.get("tie_key")
    if isinstance(explicit, tuple) and explicit and all(type(value) is int for value in explicit):
        return explicit
    try:
        if profile_id.startswith("U:"):
            _prefix, user, action = profile_id.split(":")
            return (1, int(user), int(action))
        if profile_id.startswith("J:"):
            origin, destination = profile_id[2:].split("->")
            origin_satellite, origin_cell = origin.split(":")
            destination_satellite, destination_cell = destination.split(":")
            return (
                2, int(origin_satellite), int(origin_cell),
                int(destination_satellite), int(destination_cell),
            )
    except (TypeError, ValueError):
        pass
    raise C3SPolicyError(f"{profile_id} lacks the fixed S0 tuple tie key")


def select_candidate(
    candidates: Sequence[Mapping[str, object]], *, eta_ref: Fraction,
) -> Mapping[str, object]:
    """Apply S0 exactly: service guard, exact score, BASE-first lexical ties."""

    if not candidates:
        raise C3SPolicyError("candidate catalog is empty")
    base_rows = [row for row in candidates if row.get("profile_id") == "BASE"]
    if len(base_rows) != 1 or candidates[0].get("profile_id") != "BASE":
        raise C3SPolicyError("catalog must contain BASE exactly once and first")
    base_nominal = base_rows[0].get("nominal")
    if not isinstance(base_nominal, Mapping):
        raise C3SPolicyError("BASE nominal metric is absent")
    base_metric = _metric(base_nominal, label="BASE nominal")
    threshold = int(base_metric["served"])
    seen: set[str] = set()
    eligible: list[tuple[Fraction, tuple[int, ...], Mapping[str, object]]] = []
    for row in candidates:
        profile_id = row.get("profile_id")
        nominal = row.get("nominal")
        actions = np.asarray(row.get("actions"))
        if not isinstance(profile_id, str) or not profile_id or profile_id in seen:
            raise C3SPolicyError("catalog profile IDs are malformed or duplicated")
        seen.add(profile_id)
        if not isinstance(nominal, Mapping):
            raise C3SPolicyError(f"{profile_id} nominal metric is absent")
        parsed = _metric(nominal, label=f"{profile_id} nominal")
        if parsed["opportunities"] != base_metric["opportunities"]:
            raise C3SPolicyError("candidate opportunity count differs from BASE")
        if actions.ndim != 1 or actions.dtype.kind not in "iu":
            raise C3SPolicyError(f"{profile_id} action vector is malformed")
        if int(parsed["served"]) >= threshold:
            eligible.append((nominal_score(parsed, eta_ref), _tie_key(row), row))
    if not eligible:
        raise C3SPolicyError("nominal service guard has no feasible candidate")
    best = max(row[0] for row in eligible)
    return min((row for row in eligible if row[0] == best), key=lambda row: row[1])[2]


def _metric_from_e1_payload(payload: object, *, label: str) -> dict[str, object]:
    try:
        return s0.metric_from_tape(payload, label=label)
    except s0.ProbeError as error:
        raise C3SPolicyError(str(error)) from error


def _evacuation_skeletons(
    observation: Any, reference: np.ndarray, base_profile: Any,
) -> tuple[dict[str, object], ...]:
    """Action-only projection of E1 ``build_joint_witness_catalog``."""

    origins: dict[tuple[int, int], list[int]] = {}
    for user in range(base_profile.users):
        if bool(base_profile.served[user]):
            origin = (
                int(base_profile.serving_satellite[user]),
                int(base_profile.serving_cell[user]),
            )
            origins.setdefault(origin, []).append(user)
    rows: list[dict[str, object]] = []
    for origin in sorted(origins):
        users = tuple(origins[origin])
        legal_maps = tuple(e1._legal_key_actions(observation, user) for user in users)
        common = set(legal_maps[0])
        for mapping in legal_maps[1:]:
            common.intersection_update(mapping)
        common.discard(origin)
        for destination in sorted(common):
            actions = np.asarray(reference, dtype=np.int64).copy()
            for user, mapping in zip(users, legal_maps, strict=True):
                actions[user] = mapping[destination]
            rows.append({
                "profile_id": (
                    f"J:{origin[0]}:{origin[1]}"
                    f"->{destination[0]}:{destination[1]}"
                ),
                "kind": "joint", "actions": actions,
                "tie_key": (2, *origin, *destination),
            })
    return tuple(rows)


def build_s0_catalog(
    *, step_env: Any, observation: Any, base_actions: np.ndarray,
    rng: np.random.Generator, interval_s: float,
    timing_out: dict[str, float] | None = None,
) -> tuple[dict[str, object], ...]:
    """Build BASE, every F1 unilateral, then every E1 evacuation in donor order."""

    reference = np.asarray(base_actions)
    if reference.dtype.kind not in "iu" or reference.ndim != 1:
        raise C3SPolicyError("BASE action vector is malformed")
    try:
        evaluation_started = time.perf_counter()
        # Origin membership comes from BASE's nominal/native service result.
        with s0.nominal_no_fading(step_env):
            base_evaluation = e1._evaluate_actions_neutral(step_env, reference, rng)
            base_profile, base_link_power = f1.profile_from_evaluation(
                base_evaluation, interval_s=interval_s
            )
            del base_link_power
            base_nominal = _metric_from_e1_payload(
                e1._profile_metrics(base_profile), label="BASE nominal evaluation"
            )
        base_evaluation_seconds = time.perf_counter() - evaluation_started
        enumeration_started = time.perf_counter()
        # F1 and E1 retain ownership of physical-key legality and ordering.
        unilateral = f1.enumerate_unilateral_candidates(observation, reference)
        rows: list[dict[str, object]] = [{
            "profile_id": "BASE", "kind": "base", "tie_key": (0,),
            "actions": reference.astype(np.int64, copy=True), "nominal": base_nominal,
        }]
        for skeleton in unilateral:
            actions = np.asarray(skeleton["candidate_joint_actions"], dtype=np.int64)
            rows.append({
                "profile_id": f"U:{skeleton['focal_user']}:{skeleton['candidate_action']}",
                "kind": "unilateral", "actions": actions.copy(),
                "tie_key": (1, int(skeleton["focal_user"]), int(skeleton["candidate_action"])),
            })
        rows.extend(_evacuation_skeletons(observation, reference, base_profile))
        enumeration_seconds = time.perf_counter() - enumeration_started

        # One exhaustive S0 pass.  Physical aliases retain their catalog rows
        # but share the first nominal result by complete action-vector key.
        nominal_started = time.perf_counter()
        cache = {tuple(int(value) for value in reference.tolist()): base_nominal}
        for row in rows[1:]:
            actions = np.asarray(row["actions"], dtype=np.int64)
            key = tuple(int(value) for value in actions.tolist())
            if key not in cache:
                cache[key] = s0._nominal_metric(
                    e1, f1, step_env, actions, rng, interval_s
                )
            row["nominal"] = cache[key]
        nominal_seconds = time.perf_counter() - nominal_started
        if timing_out is not None:
            timing_out.update({
                "base_nominal_evaluation": base_evaluation_seconds,
                "enumeration": enumeration_seconds,
                "remaining_nominal_evaluations": nominal_seconds,
                "unique_nominal_evaluations": float(len(cache)),
            })
    except C3SPolicyError:
        raise
    except Exception as error:
        raise C3SPolicyError("S0/E1 candidate catalog construction failed") from error
    return tuple(rows)


@dataclass(frozen=True)
class DecisionResult:
    actions: np.ndarray
    base_actions: np.ndarray
    profile_id: str
    catalog_size: int
    counts: Mapping[str, int]
    nominal: Mapping[str, object] = field(default_factory=dict)
    phase_wall_seconds: Mapping[str, float] = field(default_factory=dict)
    unique_nominal_evaluations: int = 0


DecisionFunction = Callable[["C3SPolicyAdapter", Any, Any, np.random.Generator], DecisionResult]


class C3SPolicyAdapter:
    """A state-neutral policy adapter around authenticated Q1/Q2 and S0."""

    def __init__(
        self, *, physical: Any, frozen: Any, eta_ref: Fraction | None = None,
        eta_config: Path = CONFIG_PATH, decision_function: DecisionFunction | None = None,
    ) -> None:
        self.physical = physical
        self.frozen = frozen
        self.eta_ref = load_eta_ref(eta_config) if eta_ref is None else Fraction(eta_ref)
        if self.eta_ref <= 0:
            raise C3SPolicyError("eta_ref must be positive")
        self._decision_function = decision_function or _real_decision
        self.decision_records: list[dict[str, object]] = []

    def select_actions(
        self, step_env: Any, observation: Any, rng: np.random.Generator,
    ) -> np.ndarray:
        if not isinstance(rng, np.random.Generator):
            raise C3SPolicyError("policy RNG must be numpy.random.Generator")
        try:
            before = e1._evaluation_snapshot(step_env, rng)
        except Exception as error:
            raise C3SPolicyError("cannot snapshot the pre-decision environment") from error
        original_physics = getattr(step_env, "physics", None)
        original_field = getattr(step_env, "_fading_field", None)
        started = time.perf_counter()
        result: DecisionResult | None = None
        decision_error: BaseException | None = None
        try:
            result = self._decision_function(self, step_env, observation, rng)
        except BaseException as error:
            decision_error = error
        elapsed = time.perf_counter() - started
        try:
            e1._assert_evaluation_neutral(step_env, rng, before)
        except Exception as error:
            raise C3SPolicyError("candidate evaluation changed environment state or RNG") from error
        if getattr(step_env, "physics", None) != original_physics or getattr(
            step_env, "_fading_field", None
        ) is not original_field:
            raise C3SPolicyError("nominal evaluation did not restore physics/fading state")
        if decision_error is not None:
            raise decision_error
        assert result is not None
        actions = np.asarray(result.actions)
        base = np.asarray(result.base_actions)
        if actions.dtype.kind not in "iu" or actions.ndim != 1 or actions.shape != base.shape:
            raise C3SPolicyError("selected complete action vector is malformed")
        self.decision_records.append({
            "decision_index": len(self.decision_records),
            "wall_seconds_hex": elapsed.hex(),
            "catalog_size": result.catalog_size,
            "unique_nominal_evaluations": result.unique_nominal_evaluations,
            "profile_counts": dict(result.counts),
            "selected_profile_id": result.profile_id,
            "selected_nominal": {
                "total_bits_hex": float(result.nominal["total_bits"]).hex(),
                "total_energy_j_hex": float(result.nominal["total_energy_j"]).hex(),
                "served": int(result.nominal["served"]),
                "opportunities": int(result.nominal["opportunities"]),
            } if result.nominal else None,
            "action_changed": not np.array_equal(actions, base),
            "nominal_convention": NOMINAL_CONVENTION,
            "phase_wall_seconds_hex": {
                name: float(value).hex() for name, value in result.phase_wall_seconds.items()
            },
            "peak_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        })
        return actions.astype(np.int64, copy=True)


def _real_decision(
    adapter: C3SPolicyAdapter, step_env: Any, observation: Any,
    rng: np.random.Generator,
) -> DecisionResult:
    phases: dict[str, float] = {}
    q_started = time.perf_counter()
    try:
        _native, _q12, base = e1._q12_surface_base_only(
            adapter.physical, adapter.frozen, step_env, observation
        )
        interval_s = float(step_env.driver.config.ephemeris.time_step_s)
    except Exception as error:
        raise C3SPolicyError("authenticated Q1+Q2 BASE proposal failed") from error
    phases["q_inference"] = time.perf_counter() - q_started
    catalog_started = time.perf_counter()
    catalog = build_s0_catalog(
        step_env=step_env, observation=observation, base_actions=base,
        rng=rng, interval_s=interval_s, timing_out=phases,
    )
    phases["catalog_total"] = time.perf_counter() - catalog_started
    unique_nominal_evaluations = int(phases.pop("unique_nominal_evaluations"))
    selection_started = time.perf_counter()
    selected = select_candidate(catalog, eta_ref=adapter.eta_ref)
    phases["selection"] = time.perf_counter() - selection_started
    counts = {
        kind: sum(row["kind"] == kind for row in catalog)
        for kind in ("base", "unilateral", "joint")
    }
    return DecisionResult(
        actions=np.asarray(selected["actions"], dtype=np.int64),
        base_actions=np.asarray(base, dtype=np.int64),
        profile_id=str(selected["profile_id"]),
        catalog_size=len(catalog),
        counts=counts,
        nominal=dict(selected["nominal"]),
        phase_wall_seconds=phases,
        unique_nominal_evaluations=unique_nominal_evaluations,
    )


__all__ = [
    "C3SPolicyAdapter", "C3SPolicyError", "DecisionResult", "build_s0_catalog",
    "fraction_payload", "load_eta_ref", "nominal_score", "select_candidate",
]
