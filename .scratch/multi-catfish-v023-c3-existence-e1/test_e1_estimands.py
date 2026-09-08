"""Exact E1 estimand tests against exhaustive tiny-panel enumeration."""

from __future__ import annotations

from fractions import Fraction
import copy
import itertools

import pytest

import e1_estimands as e1


def _option(profile_id: str, bits: float, energy: float, served: int, opportunities: int = 1000) -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "total_bits": bits,
        "total_energy_j": energy,
        "served": served,
        "opportunities": opportunities,
    }


def _panel(rows: list[tuple[dict[str, object], list[dict[str, object]]]], field: str = "unilateral_profiles") -> list[dict[str, object]]:
    return [
        {"anchor_id": f"a{index}", "base": base, field: candidates}
        for index, (base, candidates) in enumerate(rows)
    ]


def _brute(panel: list[dict[str, object]], field: str) -> tuple[Fraction, tuple[str, ...]]:
    options = [[row["base"], *row[field]] for row in panel]
    base_served = sum(int(row["base"]["served"]) for row in panel)
    opportunities = sum(int(row["base"]["opportunities"]) for row in panel)
    threshold = Fraction(base_served) - Fraction(
        e1.SERVICE_MARGIN_NUMERATOR * opportunities,
        e1.SERVICE_MARGIN_DENOMINATOR,
    )
    required = -((-threshold.numerator) // threshold.denominator)
    best: Fraction | None = None
    best_ids: tuple[str, ...] | None = None
    for combination in itertools.product(*options):
        if sum(int(row["served"]) for row in combination) < required:
            continue
        bits = sum((Fraction.from_float(float(row["total_bits"])) for row in combination), Fraction())
        energy = sum((Fraction.from_float(float(row["total_energy_j"])) for row in combination), Fraction())
        ratio = bits / energy
        ids = tuple(str(row["profile_id"]) for row in combination)
        if best is None or ratio > best or (ratio == best and ids < best_ids):
            best = ratio
            best_ids = ids
    assert best is not None and best_ids is not None
    return best, best_ids


@pytest.mark.parametrize(
    "panel",
    [
        _panel([
            (_option("BASE", 100.0, 100.0, 1000), [_option("x", 300.0, 100.0, 998)]),
            (_option("BASE", 100.0, 100.0, 1000), [_option("y", 180.0, 100.0, 999)]),
        ]),
        _panel([
            (_option("BASE", 10.0, 10.0, 1000), [_option("x", 15.0, 10.0, 1000)]),
            (_option("BASE", 20.0, 20.0, 1000), [_option("y", 50.0, 20.0, 1000)]),
        ]),
        _panel([
            (_option("BASE", 13.0, 7.0, 1000), [
                _option("x", 29.0, 11.0, 999),
                _option("x2", 37.0, 17.0, 1000),
            ]),
            (_option("BASE", 19.0, 23.0, 1000), [
                _option("y", 43.0, 31.0, 999),
                _option("y2", 5.0, 3.0, 1000),
            ]),
            (_option("BASE", 31.0, 29.0, 1000), [
                _option("z", 71.0, 41.0, 998),
            ]),
        ]),
    ],
    ids=["service-binding", "service-nonbinding", "variable-energy"],
)
def test_u1_matches_bruteforce(panel: list[dict[str, object]]) -> None:
    expected, ids = _brute(panel, "unilateral_profiles")
    result = e1.solve_u1(panel)
    assert Fraction.from_float(result["U1"]) == Fraction.from_float(float(expected))
    assert tuple(result["chosen_profiles"].values()) == ids
    assert result["certificate"]["global_upper_bound_proved"] is True
    assert e1.verify_certificate(panel, result, candidate_field="unilateral_profiles")


def test_service_constraint_excludes_unconstrained_best_and_binds() -> None:
    panel = _panel([
        (_option("BASE", 100.0, 100.0, 1000), [_option("x", 300.0, 100.0, 998)]),
        (_option("BASE", 100.0, 100.0, 1000), [_option("y", 180.0, 100.0, 999)]),
    ])
    result = e1.solve_u1(panel)
    assert result["chosen_profiles"] == {"a0": "x", "a1": "BASE"}
    assert result["pooled"]["served"] == result["pooled"]["minimum_served"] == 1998


def test_degenerate_ties_are_deterministic() -> None:
    panel = _panel([
        (_option("BASE", 10.0, 10.0, 1000), [
            _option("z", 20.0, 10.0, 1000),
            _option("a", 20.0, 10.0, 1000),
        ])
    ])
    first = e1.solve_u1(panel)
    second = e1.solve_u1(list(reversed(panel)))
    assert first == second
    assert first["chosen_profiles"] == {"a0": "a"}


def test_all_base_optimum() -> None:
    panel = _panel([
        (_option("BASE", 20.0, 10.0, 1000), [_option("worse", 10.0, 10.0, 1000)]),
        (_option("BASE", 30.0, 10.0, 1000), [_option("also-worse", 5.0, 10.0, 1000)]),
    ])
    result = e1.solve_u1(panel)
    assert set(result["chosen_profiles"].values()) == {"BASE"}
    assert result["U1"] == result["eta_BASE"]


def test_base_wins_exact_tie_against_candidate() -> None:
    panel = _panel([
        (_option("BASE", 20.0, 10.0, 1000), [_option("candidate", 40.0, 20.0, 1000)])
    ])
    result = e1.solve_u1(panel)
    assert result["chosen_profiles"] == {"a0": "BASE"}


def test_same_served_dominance_survivor_changes_with_q() -> None:
    panel = e1._canonical_anchors(_panel([
        (_option("BASE", 10.0, 2.0, 1000), [_option("crossing", 20.0, 10.0, 1000)])
    ]), candidate_field="unilateral_profiles")
    low = e1._choice_set_census(panel, q=Fraction(0))["anchors"][0]
    high = e1._choice_set_census(panel, q=Fraction(2))["anchors"][0]
    assert low["final_q_survivors_by_served"] == {"1000": "crossing"}
    assert high["final_q_survivors_by_served"] == {"1000": "BASE"}


def test_j1_matches_bruteforce() -> None:
    panel = _panel([
        (_option("BASE", 10.0, 10.0, 1000), [_option("joint-a", 25.0, 10.0, 1000)]),
        (_option("BASE", 10.0, 10.0, 1000), [_option("joint-b", 11.0, 9.0, 1000)]),
    ], field="joint_profiles")
    expected, ids = _brute(panel, "joint_profiles")
    result = e1.solve_j1(panel)
    assert result["J1"] == float(expected)
    assert tuple(result["chosen_profiles"].values()) == ids
    assert e1.verify_certificate(panel, result, candidate_field="joint_profiles")


def test_certificate_mutation_is_rejected() -> None:
    panel = _panel([
        (_option("BASE", 10.0, 10.0, 1000), [_option("better", 20.0, 10.0, 1000)])
    ])
    result = e1.solve_u1(panel)
    result["certificate"]["optimal_ratio_exact"]["numerator"] = "1"
    with pytest.raises(e1.E1EstimandError, match="certificate"):
        e1.verify_certificate(panel, result, candidate_field="unilateral_profiles")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda result: result["certificate"]["coefficients"][0]["profiles"][0]["bits"].__setitem__("numerator", "11"),
        lambda result: result["certificate"]["chosen_residual_exact"].__setitem__("numerator", "1"),
        lambda result: result["certificate"].__setitem__("feasible", False),
        lambda result: result["certificate"]["dp_trace"][0]["retained_states"][0]["backpointer"].__setitem__("chosen_profile_id", "mutated"),
        lambda result: result["certificate"].__setitem__("minimum_served", 998),
    ],
    ids=["coefficient", "residual", "feasibility", "backpointer", "minimum-service"],
)
def test_authoritative_proof_field_mutations_are_rejected(mutate: object) -> None:
    panel = _panel([
        (_option("BASE", 10.0, 10.0, 1000), [_option("better", 20.0, 10.0, 1000)])
    ])
    result = copy.deepcopy(e1.solve_u1(panel))
    mutate(result)
    with pytest.raises(e1.E1EstimandError):
        e1.verify_certificate(panel, result, candidate_field="unilateral_profiles")


def test_independent_serialized_witness_arithmetic() -> None:
    panel = _panel([
        (_option("BASE", 7.0, 3.0, 1000), [_option("x", 11.0, 4.0, 999)]),
        (_option("BASE", 13.0, 5.0, 1000), [_option("y", 17.0, 6.0, 1000)]),
    ])
    result = e1.solve_u1(panel)
    checked = e1._independent_serialized_witness_check(
        result["certificate"], result["chosen_profiles"]
    )
    assert checked["residual"] == 0
    assert checked["served"] >= result["certificate"]["minimum_served"]
    assert checked["bits"] / checked["energy"] == checked["q"]
