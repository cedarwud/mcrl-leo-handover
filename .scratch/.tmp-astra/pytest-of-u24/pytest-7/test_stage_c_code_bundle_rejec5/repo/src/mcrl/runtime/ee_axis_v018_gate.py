"""Pure adjudication for the V0.18 three-arm analytic diagnostic.

This module contains no simulator, learner, checkpoint loading, or file I/O.
It validates a rectangular matched panel and applies the pre-outcome mechanical
decision order: mechanics first, then the exact-ZR upper bound, then nominal
observability.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

from ..errors import MCRLContractError


V018_ARMS = ("BASE", "EXACT_ZR", "NOMINAL_ZR")
V018_SERVICE_NONINFERIORITY_MARGIN = 0.001


class V018GateError(MCRLContractError):
    """The V0.18 diagnostic panel is malformed or not paired."""


def _finite_positive(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise V018GateError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise V018GateError(f"{field} must be finite and positive")
    return result


def _integer(value: object, *, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise V018GateError(f"{field} must be an integer >= {minimum}")
    return int(value)


def _identity(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise V018GateError(f"{field} must be a nonempty string")
    return value


def _ordered_unique(values: Sequence[int], *, field: str) -> tuple[int, ...]:
    result = tuple(int(value) for value in values)
    if not result or len(result) != len(set(result)):
        raise V018GateError(f"{field} must be nonempty and unique")
    return result


def _pool(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int]:
    if not rows:
        raise V018GateError("cannot pool an empty row set")
    bits = math.fsum(
        _finite_positive(row.get("total_bits"), field="total_bits") for row in rows
    )
    energy = math.fsum(
        _finite_positive(row.get("total_energy_j"), field="total_energy_j")
        for row in rows
    )
    served = sum(
        _integer(row.get("served_user_steps"), field="served_user_steps")
        for row in rows
    )
    opportunities = sum(
        _integer(
            row.get("served_opportunities"),
            field="served_opportunities",
            minimum=1,
        )
        for row in rows
    )
    if served > opportunities:
        raise V018GateError("served_user_steps exceed served_opportunities")
    return {
        "row_count": len(rows),
        "total_bits": bits,
        "total_energy_j": energy,
        "ratio_of_sums_ee_bits_per_j": bits / energy,
        "served_user_steps": served,
        "served_opportunities": opportunities,
        "served_fraction": served / opportunities,
    }


def _contrast(
    indexed: Mapping[tuple[int, str, int], Mapping[str, Any]],
    *,
    treatment: str,
    worlds: tuple[int, ...],
    lineages: tuple[int, ...],
) -> dict[str, Any]:
    base_rows = [indexed[(world, "BASE", lineage)] for world in worlds for lineage in lineages]
    treatment_rows = [
        indexed[(world, treatment, lineage)]
        for world in worlds
        for lineage in lineages
    ]
    base_pool = _pool(base_rows)
    treatment_pool = _pool(treatment_rows)
    base_ee = float(base_pool["ratio_of_sums_ee_bits_per_j"])
    treatment_ee = float(treatment_pool["ratio_of_sums_ee_bits_per_j"])
    relative = treatment_ee / base_ee - 1.0

    by_world: dict[str, dict[str, float]] = {}
    positive_world_count = 0
    for world in worlds:
        base = _pool([indexed[(world, "BASE", lineage)] for lineage in lineages])
        arm = _pool([indexed[(world, treatment, lineage)] for lineage in lineages])
        delta = (
            float(arm["ratio_of_sums_ee_bits_per_j"])
            / float(base["ratio_of_sums_ee_bits_per_j"])
            - 1.0
        )
        positive_world_count += int(delta > 0.0)
        by_world[str(world)] = {"relative_delta_ee": delta}

    by_lineage: dict[str, dict[str, float]] = {}
    positive_lineage_count = 0
    for lineage in lineages:
        base = _pool([indexed[(world, "BASE", lineage)] for world in worlds])
        arm = _pool([indexed[(world, treatment, lineage)] for world in worlds])
        delta = (
            float(arm["ratio_of_sums_ee_bits_per_j"])
            / float(base["ratio_of_sums_ee_bits_per_j"])
            - 1.0
        )
        positive_lineage_count += int(delta > 0.0)
        by_lineage[str(lineage)] = {"relative_delta_ee": delta}

    served_difference = (
        int(treatment_pool["served_user_steps"])
        - int(base_pool["served_user_steps"])
    )
    opportunities = int(base_pool["served_opportunities"])
    if opportunities != int(treatment_pool["served_opportunities"]):
        raise V018GateError("matched arms have different service opportunities")
    service_noninferior = (
        served_difference
        + V018_SERVICE_NONINFERIORITY_MARGIN * opportunities
        >= -1e-12
    )
    passed = bool(
        relative > 0.0
        and positive_world_count >= min(3, len(worlds))
        and positive_lineage_count >= min(2, len(lineages))
        and service_noninferior
    )
    return {
        "passed": passed,
        "relative_delta_ee": relative,
        "positive_world_count": positive_world_count,
        "positive_lineage_count": positive_lineage_count,
        "served_user_step_delta": served_difference,
        "served_fraction_delta": (
            float(treatment_pool["served_fraction"])
            - float(base_pool["served_fraction"])
        ),
        "service_noninferior": service_noninferior,
        "base": base_pool,
        "treatment": treatment_pool,
        "by_world": by_world,
        "by_lineage": by_lineage,
    }


def adjudicate_v018_analytic_gate(
    rows: Sequence[Mapping[str, Any]],
    *,
    worlds: Sequence[int],
    lineages: Sequence[int],
    compatibility_proof_passed: bool,
    source_diagnostics_passed: bool,
) -> dict[str, Any]:
    """Apply the frozen V0.18 stop order to one complete matched panel."""

    world_values = _ordered_unique(worlds, field="worlds")
    lineage_values = _ordered_unique(lineages, field="lineages")
    if type(compatibility_proof_passed) is not bool:
        raise V018GateError("compatibility_proof_passed must be Boolean")
    if type(source_diagnostics_passed) is not bool:
        raise V018GateError("source_diagnostics_passed must be Boolean")

    indexed: dict[tuple[int, str, int], Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise V018GateError("each panel row must be a mapping")
        world = _integer(row.get("world_seed"), field="world_seed", minimum=1)
        lineage = _integer(row.get("lineage"), field="lineage", minimum=1)
        arm = row.get("arm")
        if arm not in V018_ARMS:
            raise V018GateError("row arm is outside the V0.18 declaration")
        key = (world, str(arm), lineage)
        if key in indexed:
            raise V018GateError("duplicate rectangular panel row")
        indexed[key] = row

    expected = {
        (world, arm, lineage)
        for world in world_values
        for arm in V018_ARMS
        for lineage in lineage_values
    }
    if set(indexed) != expected:
        raise V018GateError("panel is not a complete rectangular matched panel")

    for world in world_values:
        matched = [
            indexed[(world, arm, lineage)]
            for arm in V018_ARMS
            for lineage in lineage_values
        ]
        if len(
            {
                _identity(row.get("initial_world_sha256"), field="initial_world_sha256")
                for row in matched
            }
        ) != 1:
            raise V018GateError("matched arms do not share one initial world")
        if len(
            {
                _identity(row.get("field_root_digest"), field="field_root_digest")
                for row in matched
            }
        ) != 1:
            raise V018GateError("matched arms do not share one common field")

    for lineage in lineage_values:
        matched = [
            indexed[(world, arm, lineage)]
            for world in world_values
            for arm in V018_ARMS
        ]
        for name in ("q1_checkpoint_sha256", "q2_checkpoint_sha256"):
            if len({_identity(row.get(name), field=name) for row in matched}) != 1:
                raise V018GateError(f"matched rows do not share one {name}")

    mechanics_passed = all(
        row.get("mechanics_passed") is True for row in indexed.values()
    )
    contrasts = {
        arm: _contrast(
            indexed,
            treatment=arm,
            worlds=world_values,
            lineages=lineage_values,
        )
        for arm in ("EXACT_ZR", "NOMINAL_ZR")
    }

    if not compatibility_proof_passed or not mechanics_passed:
        decision = "STOP_V018_MECHANICS"
    elif not bool(contrasts["EXACT_ZR"]["passed"]):
        decision = "STOP_ZR_IN_LEARNED_Q2_CONTEXT"
    elif not bool(contrasts["NOMINAL_ZR"]["passed"]) or not source_diagnostics_passed:
        decision = "STOP_RELATIONAL_OBSERVABILITY"
    else:
        decision = "PASS_ANALYTIC_DIAGNOSTIC"

    return {
        "decision": decision,
        "passed": decision == "PASS_ANALYTIC_DIAGNOSTIC",
        "compatibility_proof_passed": compatibility_proof_passed,
        "mechanics_passed": mechanics_passed,
        "source_diagnostics_passed": source_diagnostics_passed,
        "service_noninferiority_margin": V018_SERVICE_NONINFERIORITY_MARGIN,
        "worlds": list(world_values),
        "lineages": list(lineage_values),
        "contrasts": contrasts,
    }


__all__ = [
    "V018_ARMS",
    "V018_SERVICE_NONINFERIORITY_MARGIN",
    "V018GateError",
    "adjudicate_v018_analytic_gate",
]
