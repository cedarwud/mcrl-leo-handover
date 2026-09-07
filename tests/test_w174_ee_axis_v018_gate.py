from __future__ import annotations

import pytest

from mcrl.runtime.ee_axis_v018_gate import (
    V018GateError,
    adjudicate_v018_analytic_gate,
)


WORLDS = (11, 12, 13, 14)
LINEAGES = (21, 22, 23)


def _rows(
    *,
    exact_multiplier: float = 1.02,
    nominal_multiplier: float = 1.01,
    nominal_bad_worlds: frozenset[int] = frozenset(),
    exact_bad_lineages: frozenset[int] = frozenset(),
    served_delta: int = 0,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for world in WORLDS:
        for lineage in LINEAGES:
            base_bits = 100.0
            base_energy = 10.0
            common = {
                "world_seed": world,
                "lineage": lineage,
                "initial_world_sha256": f"world-{world}",
                "field_root_digest": f"field-{world}",
                "q1_checkpoint_sha256": f"q1-{lineage}",
                "q2_checkpoint_sha256": f"q2-{lineage}",
                "mechanics_passed": True,
            }
            rows.append(
                {
                    **common,
                    "arm": "BASE",
                    "total_bits": base_bits,
                    "total_energy_j": base_energy,
                    "served_user_steps": 1000,
                    "served_opportunities": 1000,
                }
            )
            exact = 0.98 if lineage in exact_bad_lineages else exact_multiplier
            rows.append(
                {
                    **common,
                    "arm": "EXACT_ZR",
                    "total_bits": base_bits * exact,
                    "total_energy_j": base_energy,
                    "served_user_steps": 1000 + served_delta,
                    "served_opportunities": 1000,
                }
            )
            nominal = 0.98 if world in nominal_bad_worlds else nominal_multiplier
            rows.append(
                {
                    **common,
                    "arm": "NOMINAL_ZR",
                    "total_bits": base_bits * nominal,
                    "total_energy_j": base_energy,
                    "served_user_steps": 1000 + served_delta,
                    "served_opportunities": 1000,
                }
            )
    return rows


def test_pass_requires_both_positive_arms_and_source_gate() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert result["decision"] == "PASS_ANALYTIC_DIAGNOSTIC"
    assert result["passed"] is True
    assert result["contrasts"]["EXACT_ZR"]["positive_world_count"] == 4
    assert result["contrasts"]["NOMINAL_ZR"]["positive_lineage_count"] == 3


def test_compatibility_is_a_pre_arm_mechanics_stop() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=False,
        source_diagnostics_passed=True,
    )
    assert result["decision"] == "STOP_V018_MECHANICS"


def test_exact_failure_precedes_nominal_failure() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(exact_multiplier=0.98, nominal_multiplier=0.97),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=False,
    )
    assert result["decision"] == "STOP_ZR_IN_LEARNED_Q2_CONTEXT"


def test_nominal_failure_has_observability_stop() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(nominal_multiplier=0.98),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert result["decision"] == "STOP_RELATIONAL_OBSERVABILITY"


def test_world_and_lineage_direction_counts_are_binding() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(nominal_bad_worlds=frozenset({11, 12})),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert result["decision"] == "STOP_RELATIONAL_OBSERVABILITY"
    assert result["contrasts"]["NOMINAL_ZR"]["positive_world_count"] == 2


def test_service_noninferiority_margin_is_absolute_one_per_thousand() -> None:
    passing = adjudicate_v018_analytic_gate(
        _rows(served_delta=-1),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert passing["decision"] == "PASS_ANALYTIC_DIAGNOSTIC"

    failing = adjudicate_v018_analytic_gate(
        _rows(served_delta=-2),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert failing["decision"] == "STOP_ZR_IN_LEARNED_Q2_CONTEXT"


def test_source_failure_stops_only_after_exact_trajectory_passes() -> None:
    result = adjudicate_v018_analytic_gate(
        _rows(),
        worlds=WORLDS,
        lineages=LINEAGES,
        compatibility_proof_passed=True,
        source_diagnostics_passed=False,
    )
    assert result["decision"] == "STOP_RELATIONAL_OBSERVABILITY"


def test_rejects_incomplete_or_unpaired_panels() -> None:
    rows = _rows()
    rows.pop()
    with pytest.raises(V018GateError, match="rectangular"):
        adjudicate_v018_analytic_gate(
            rows,
            worlds=WORLDS,
            lineages=LINEAGES,
            compatibility_proof_passed=True,
            source_diagnostics_passed=True,
        )

    rows = _rows()
    rows[-1]["field_root_digest"] = "different-field"
    with pytest.raises(V018GateError, match="common field"):
        adjudicate_v018_analytic_gate(
            rows,
            worlds=WORLDS,
            lineages=LINEAGES,
            compatibility_proof_passed=True,
            source_diagnostics_passed=True,
        )
