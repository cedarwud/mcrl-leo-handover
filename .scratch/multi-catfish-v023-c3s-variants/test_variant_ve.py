from __future__ import annotations

from fractions import Fraction
import hashlib
from types import SimpleNamespace

import numpy as np

import run_v023_c3s_variants as runner
import variant_policy as policy


# Provenance: all small numeric values below are declared synthetic fixtures, not scientific constants.
def _metric(bits: float, energy: float, served: int = 2) -> dict[str, object]:
    return {
        "total_bits": bits,
        "total_energy_j": energy,
        "served": served,
        "opportunities": 2,
    }


def _row(profile_id: str, actions: list[int], nominal: dict[str, object]) -> dict[str, object]:
    return {
        "profile_id": profile_id,
        "kind": "base" if profile_id == "BASE" else "unilateral",
        "tie_key": (0,) if profile_id == "BASE" else (1, 0, actions[0]),
        "actions": np.asarray(actions, dtype=np.int64),
        "nominal": nominal,
    }


def test_scenario_seeds_are_reproducible_and_independent_of_world_seed(monkeypatch) -> None:
    # Provenance: expected values are direct applications of the declared SHA-256/int63 rule.
    expected = (
        6018382882959041944,
        817005370450305563,
        1936779116122867599,
        908075962035052284,
    )
    assert policy.ve_scenario_seeds() == expected
    monkeypatch.setattr(runner, "WORLDS", tuple(reversed(runner.WORLDS)))
    assert policy.ve_scenario_seeds() == expected
    for index, seed in enumerate(expected, start=1):
        domain = f"C3S_VE/scenario/{index}"
        assert policy.derive_ve_scenario_seed(domain) == seed


def test_path_keyed_common_random_numbers_survive_candidate_satellite_set_changes() -> None:
    seed = policy.ve_scenario_seeds()[0]
    field = policy.ve_fading_field(seed)
    # Provenance: satellite IDs, user count, step, and elevations are tiny synthetic CRN fixtures.
    shared_norad, left_norad, right_norad = 22, 11, 33
    users, step = 3, 2
    left_elevation = {
        left_norad: np.asarray([30.0, 40.0, 50.0]),
        shared_norad: np.asarray([35.0, 45.0, 55.0]),
    }
    right_elevation = {
        shared_norad: left_elevation[shared_norad],
        right_norad: np.asarray([25.0, 35.0, 45.0]),
    }
    left = field.draw(
        event="physics", step_index=step, norad_ids=left_elevation,
        num_users=users, elevation_by_norad=left_elevation,
        k_factor_db=20.0,
    )
    right = field.draw(
        event="physics", step_index=step, norad_ids=right_elevation,
        num_users=users, elevation_by_norad=right_elevation,
        k_factor_db=20.0,
    )
    np.testing.assert_array_equal(left[0][shared_norad], right[0][shared_norad])
    np.testing.assert_array_equal(left[1][shared_norad], right[1][shared_norad])


def test_attach_expected_metrics_resets_same_scenarios_for_every_candidate() -> None:
    calls: list[tuple[int, tuple[int, ...]]] = []

    class Evaluator:
        def __init__(self, seed: int) -> None:
            self.seed = seed

        def evaluate(self, actions: np.ndarray) -> SimpleNamespace:
            calls.append((self.seed, tuple(int(value) for value in actions.tolist())))
            # Provenance: synthetic bits distinguish scenario/candidate calls; unit energy isolates ordering.
            bits = float(self.seed + int(actions.sum()))
            return SimpleNamespace(
                link_rate_bps=np.asarray([bits, 0.0]), system_power_w=1.0,
                resolution=SimpleNamespace(served_count=1),
            )

    catalog = (
        _row("BASE", [0], _metric(1.0, 1.0, served=1)),
        _row("U:0:1", [1], _metric(1.0, 1.0, served=1)),
    )
    # Provenance: two distinct seeds are the smallest synthetic CRN ordering fixture.
    scenario_seeds = (5, 7)
    result = policy.attach_expected_metrics(
        catalog, interval_s=1.0, scenario_seeds=scenario_seeds,
        evaluator_factory=Evaluator,
    )
    assert calls == [(5, (0,)), (5, (1,)), (7, (0,)), (7, (1,))]
    assert all(len(row["scenario_metrics"]) == len(scenario_seeds) for row in result)


def test_k_is_fixed_by_disabled_config_declaration() -> None:
    config = policy.load_ve_config()
    # Provenance: K=4 is fixed by Deliverable B's smallest-even/two-sided cost-cap declaration.
    assert config["scenario_count"] == 4
    assert config["enabled"] is False
    assert len(policy.ve_scenario_seeds()) == config["scenario_count"]


def test_expected_score_reduces_to_nominal_score_for_nominal_scenarios() -> None:
    nominal = _metric(19.0, 3.0)
    eta_ref = Fraction(5, 2)
    # Provenance: repetition count comes from the declared V-E K, not an observed outcome.
    scenarios = [nominal] * int(policy.load_ve_config()["scenario_count"])
    assert policy.expected_score(scenarios, eta_ref=eta_ref) == policy.v1.nominal_score(
        nominal, eta_ref,
    )


def test_nominal_service_guard_is_unchanged_for_expected_ranking() -> None:
    base = _row("BASE", [0, 0], _metric(10.0, 1.0))
    candidate = _row("U:0:1", [1, 0], _metric(10.0, 1.0, served=1))
    base["scenario_metrics"] = (_metric(10.0, 1.0),)
    candidate["scenario_metrics"] = (_metric(100.0, 1.0, served=1),)
    adapter = SimpleNamespace(
        eta_ref=Fraction(1), hooks=policy.hooks_for(policy.VE_ARM),
    )
    selected, _, _ = policy.select_with_hooks(
        (base, candidate), context=policy.DecisionContext(step_index=0), adapter=adapter,
    )
    assert selected["profile_id"] == "BASE"


def test_expected_ranking_selects_an_eligible_non_base_row() -> None:
    base = _row("BASE", [0, 0], _metric(10.0, 1.0))
    candidate = _row("U:0:1", [1, 0], _metric(10.0, 1.0))
    # Provenance: four repetitions use declared K; synthetic scores isolate eligible V-E ranking.
    base["scenario_metrics"] = (_metric(10.0, 1.0),) * 4
    candidate["scenario_metrics"] = (_metric(12.0, 1.0),) * 4
    base["service_guard_metric"] = base["scenario_metrics"][0]
    candidate["service_guard_metric"] = candidate["scenario_metrics"][0]
    adapter = SimpleNamespace(
        eta_ref=Fraction(1), hooks=policy.hooks_for(policy.VE_ARM),
    )
    selected, _, scores = policy.select_with_hooks(
        (base, candidate), context=policy.DecisionContext(step_index=0), adapter=adapter,
    )
    assert selected["profile_id"] == "U:0:1"
    assert scores["U:0:1"] > scores["BASE"]


def test_sealed_nine_arm_config_and_default_panel_digests_are_unchanged() -> None:
    assert policy.sealed_nine_arm_config_sha256() == policy.SEALED_NINE_ARM_CONFIG_SHA256
    assert runner.ARMS == (
        "BASE", "LITE", "V-J", "V-U", "V-M", "V-C", "V-H", "V-P", "V-L2",
    )
    assert policy.VE_ARM not in runner.active_arms()
    assert hashlib.sha256(runner.canonical_bytes(runner.panel_bindings())).hexdigest() == (
        "af32464f4bc68924e38899cb28d3553c9aef35200d741eb808fe111c964a2941"
    )


def test_runner_requires_explicit_opt_in_and_estimates_ve(monkeypatch) -> None:
    assert policy.VE_ARM not in runner.active_arms()
    assert runner.active_arms(enable_ve=True)[-1] == policy.VE_ARM
    panel = runner.panel_bindings(enable_ve=True)
    assert panel["ve_opt_in"]["enabled_by_cli"] is True

    # Provenance: synthetic full-arm estimate uses one evaluation and one worker-hour as unit bases.
    one = runner.fraction_payload(Fraction(1))
    monkeypatch.setattr(
        runner.v1runner, "estimate",
        lambda *, units: {
            "horizons": {str(runner.HORIZON): {"arms": {"FULL": {
                "projected_nominal_evaluations_exact": one,
                "worker_hours": 1.0,
            }}}},
            "basis": "synthetic",
        },
    )
    default = runner.estimate(units=1)
    opted_in = runner.estimate(units=1, enable_ve=True)
    assert policy.VE_ARM not in default["arms"]
    assert default["optional_arms"][policy.VE_ARM]["enabled"] is False
    assert opted_in["arms"][policy.VE_ARM]["enabled"] is True
