from __future__ import annotations

from contextlib import nullcontext
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import c3s_policy
import run_v023_c3s_screen as screen


def metric(bits: float, energy: float, served: int, opportunities: int = 2) -> dict[str, object]:
    return {
        "total_bits": bits, "total_energy_j": energy,
        "served": served, "opportunities": opportunities,
    }


def test_default_eta_ref_is_the_bound_binary64_constant() -> None:
    assert c3s_policy.load_eta_ref() == Fraction.from_float(
        float.fromhex("0x1.d94fb72305d6ap+26")
    )


class NeutralStepEnv:
    def __init__(self) -> None:
        self._previous_served_rate_bps = np.asarray([1.0, 2.0])
        self._previous_association = ((1, 2),)
        self._previous_demand = {1: 2.0}
        self._previous_link_power_w = np.asarray([3.0])
        self._previous_radiating = None
        self._segments = ("segment",)
        self._step_index = 4
        self.driver = SimpleNamespace(step_index=4)
        self._candidates = object()
        self.physics = SimpleNamespace(fading_enabled=True)
        self._fading_field = object()


def test_adapter_neutrality_preserves_state_rng_and_field() -> None:
    environment = NeutralStepEnv()
    rng = np.random.default_rng(71)
    before_rng = deepcopy(rng.bit_generator.state)
    before = c3s_policy.e1._evaluation_snapshot(environment, rng)
    field = environment._fading_field

    def decision(_adapter, _env, _observation, _rng):
        return c3s_policy.DecisionResult(
            actions=np.asarray([1, 0]), base_actions=np.asarray([0, 0]),
            profile_id="U:0:1", catalog_size=2,
            counts={"base": 1, "unilateral": 1, "joint": 0},
        )

    adapter = c3s_policy.C3SPolicyAdapter(
        physical=object(), frozen=object(), eta_ref=Fraction(1),
        decision_function=decision,
    )
    selected = adapter.select_actions(environment, object(), rng)
    assert selected.tolist() == [1, 0]
    c3s_policy.e1._assert_evaluation_neutral(environment, rng, before)
    assert rng.bit_generator.state == before_rng
    assert environment._fading_field is field
    assert adapter.decision_records[0]["catalog_size"] == 2


def test_candidate_catalog_order_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = SimpleNamespace()
    monkeypatch.setattr(c3s_policy.s0, "nominal_no_fading", lambda _env: nullcontext())
    monkeypatch.setattr(c3s_policy.e1, "_evaluate_actions_neutral", lambda *_args: object())
    monkeypatch.setattr(c3s_policy.f1, "profile_from_evaluation", lambda *_args, **_kw: (profile, np.zeros(1)))
    monkeypatch.setattr(
        c3s_policy.e1, "_profile_metrics",
        lambda _profile: {"total_bits": 10.0.hex(), "total_energy_j": 2.0.hex(), "served": 2, "opportunities": 2},
    )
    monkeypatch.setattr(
        c3s_policy.f1, "enumerate_unilateral_candidates",
        lambda *_args: (
            {"focal_user": 0, "candidate_action": 2, "candidate_joint_actions": [2, 0]},
            {"focal_user": 1, "candidate_action": 3, "candidate_joint_actions": [0, 3]},
        ),
    )
    monkeypatch.setattr(c3s_policy.s0, "_nominal_metric", lambda *_args: metric(10, 2, 2))
    monkeypatch.setattr(
        c3s_policy, "_evacuation_skeletons",
        lambda *_args: ({
            "profile_id": "J:1:2->3:4", "kind": "joint",
            "actions": np.asarray([4, 4]), "tie_key": (2, 1, 2, 3, 4),
        },),
    )
    kwargs = dict(
        step_env=object(), observation=object(), base_actions=np.asarray([0, 0]),
        rng=np.random.default_rng(9), interval_s=c3s_policy.e1.INTERVAL_S,
    )
    first = c3s_policy.build_s0_catalog(**kwargs)
    second = c3s_policy.build_s0_catalog(**kwargs)
    expected = ["BASE", "U:0:2", "U:1:3", "J:1:2->3:4"]
    assert [row["profile_id"] for row in first] == expected
    assert [row["profile_id"] for row in second] == expected


def test_lite_catalog_order_top2_ties_base_equivalence_and_all_evacuations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = SimpleNamespace()
    tables = tuple(
        SimpleNamespace(mask=np.asarray([True, True, True, True] + [False] * 24))
        for _ in range(2)
    )
    observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=tables))
    monkeypatch.setattr(c3s_policy.s0, "nominal_no_fading", lambda _env: nullcontext())
    monkeypatch.setattr(c3s_policy.e1, "_evaluate_actions_neutral", lambda *_args: object())
    monkeypatch.setattr(c3s_policy.f1, "profile_from_evaluation", lambda *_args, **_kw: (profile, np.zeros(1)))
    monkeypatch.setattr(
        c3s_policy.e1, "_profile_metrics",
        lambda _profile: {
            "total_bits": 10.0.hex(), "total_energy_j": 2.0.hex(),
            "served": 2, "opportunities": 2,
        },
    )
    # User 0 slot 2 ranks second but is BASE-equivalent and therefore absent
    # from the inherited physically-distinct rows; slot 3 is retained instead.
    monkeypatch.setattr(
        c3s_policy.f1, "enumerate_unilateral_candidates",
        lambda *_args: (
            {"focal_user": 0, "candidate_action": 1, "candidate_joint_actions": [1, 0]},
            {"focal_user": 0, "candidate_action": 3, "candidate_joint_actions": [3, 0]},
            {"focal_user": 1, "candidate_action": 1, "candidate_joint_actions": [0, 1]},
        ),
    )
    monkeypatch.setattr(c3s_policy.s0, "_nominal_metric", lambda *_args: metric(10, 2, 2))
    monkeypatch.setattr(
        c3s_policy, "_evacuation_skeletons",
        lambda *_args: ({
            "profile_id": "J:1:2->3:4", "kind": "joint",
            "actions": np.asarray([3, 3]), "tie_key": (2, 1, 2, 3, 4),
        },),
    )
    q12 = np.zeros((2, 28), dtype=np.float32)
    q12[0, :4] = [9.0, 6.0, 8.0, 7.0]
    # The runner-up tie is resolved by lowest slot index: slot 1 before slot 2.
    q12[1, :4] = [9.0, 8.0, 8.0, 7.0]
    rows = c3s_policy.build_s0_catalog(
        step_env=object(), observation=observation,
        base_actions=np.asarray([0, 0]), q12=q12, catalog="lite",
        rng=np.random.default_rng(9), interval_s=c3s_policy.e1.INTERVAL_S,
    )
    assert [row["profile_id"] for row in rows] == [
        "BASE", "U:0:3", "U:1:1", "J:1:2->3:4",
    ]


def test_selection_service_guard_and_base_first_ties() -> None:
    candidates = [
        {"profile_id": "BASE", "actions": np.asarray([0]), "nominal": metric(10, 1, 2)},
        # Better objective but below BASE nominal service: ineligible.
        {"profile_id": "J:1:1->2:2", "actions": np.asarray([1]), "nominal": metric(100, 1, 1)},
        # Exact objective tie with BASE: BASE wins explicitly.
        {"profile_id": "U:0:2", "actions": np.asarray([2]), "nominal": metric(10, 1, 2)},
    ]
    selected = c3s_policy.select_candidate(candidates, eta_ref=Fraction(1))
    assert selected["profile_id"] == "BASE"
    candidates.append(
        {"profile_id": "U:0:3", "actions": np.asarray([3]), "nominal": metric(11, 1, 2)}
    )
    assert c3s_policy.select_candidate(candidates, eta_ref=Fraction(1))["profile_id"] == "U:0:3"
    numeric_tie = [
        candidates[0],
        {"profile_id": "U:10:0", "actions": np.asarray([1]), "nominal": metric(12, 1, 2)},
        {"profile_id": "U:2:0", "actions": np.asarray([2]), "nominal": metric(12, 1, 2)},
    ]
    assert c3s_policy.select_candidate(numeric_tie, eta_ref=Fraction(1))["profile_id"] == "U:2:0"


class SyntheticObservation:
    def __init__(self, step_index: int) -> None:
        self.step_index = step_index
        self.masks = np.ones((screen.USERS, screen.f1.NUM_ACTIONS), dtype=np.bool_)


class SyntheticEnvironment:
    def __init__(self, horizon: int) -> None:
        self.horizon = horizon
        self.position = 0
        self.environment = SimpleNamespace(
            driver=SimpleNamespace(config=SimpleNamespace(
                ephemeris=SimpleNamespace(time_step_s=1.0)
            ))
        )
        self.last_outcome = None

    def reset(self, _env_rng, _mobility_rng):
        self.position = 0
        observation = SyntheticObservation(0)
        return [], [], observation

    def step(self, actions, _rng):
        self.position += int(actions[0]) + 1
        index = len(getattr(self, "history", []))
        self.history = [*getattr(self, "history", []), self.position]
        done = index == self.horizon - 1
        observation = SyntheticObservation(index + 1)
        self.last_outcome = SimpleNamespace(
            link_rate_bps=np.full(screen.USERS, float(self.position)),
            system_power_w=float(self.position + 1),
            resolution=SimpleNamespace(served_count=screen.USERS),
            done=done, observation=observation,
        )
        return SimpleNamespace(done=done)


def test_closed_loop_arms_advance_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mcrl.runtime.ee_axis_state as state_module

    monkeypatch.setattr(
        state_module, "encode_ee_axis_state",
        lambda _env, _obs: SimpleNamespace(state_sha256="a" * 64),
    )
    base_env = SyntheticEnvironment(3)
    full_env = SyntheticEnvironment(3)
    lite_env = SyntheticEnvironment(3)
    base = screen.run_arm_trajectory(
        environment=base_env, env_rng=np.random.default_rng(1),
        mobility_rng=np.random.default_rng(2), horizon=3,
        selector=lambda *_args: np.zeros(screen.USERS, dtype=np.int64),
    )
    full = screen.run_arm_trajectory(
        environment=full_env, env_rng=np.random.default_rng(1),
        mobility_rng=np.random.default_rng(2), horizon=3,
        selector=lambda *_args: np.ones(screen.USERS, dtype=np.int64),
    )
    lite = screen.run_arm_trajectory(
        environment=lite_env, env_rng=np.random.default_rng(1),
        mobility_rng=np.random.default_rng(2), horizon=3,
        selector=lambda *_args: np.full(screen.USERS, 2, dtype=np.int64),
    )
    assert len({base["initial_state_sha256"], full["initial_state_sha256"], lite["initial_state_sha256"]}) == 1
    assert base_env.history == [1, 2, 3]
    assert full_env.history == [2, 4, 6]
    assert lite_env.history == [3, 6, 9]
    assert (base_env.position, full_env.position, lite_env.position) == (3, 6, 9)


def _receipt(
    *, base: tuple[float, float, int], full: tuple[float, float, int],
    lite: tuple[float, float, int], full_changes: int, lite_changes: int,
) -> dict[str, object]:
    def trajectory(values):
        bits, energy, served = values
        return {"steps": [{
            "step_index": 0, "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
            "served": served, "opportunities": 100,
        }]}
    return {
        "arms": {"BASE": trajectory(base), "FULL": trajectory(full), "LITE": trajectory(lite)},
        "decisions_by_arm": {"FULL": [{}], "LITE": [{}]},
        "action_changes_by_arm": {"FULL": full_changes, "LITE": lite_changes},
    }


def test_exact_pooling_and_disposition_reasons() -> None:
    pooled = screen.pool_unit_receipts([
        _receipt(
            base=(0.1, 0.3, 100), full=(0.2, 0.3, 100), lite=(0.05, 0.3, 100),
            full_changes=1, lite_changes=0,
        ),
        _receipt(
            base=(0.2, 0.3, 100), full=(0.3, 0.3, 100), lite=(0.1, 0.3, 100),
            full_changes=1, lite_changes=1,
        ),
    ])
    assert pooled["decisions"]["FULL"] == {
        "outcome": "C3S_FULL_SCREEN_SUPPORT", "reasons": [],
    }
    assert pooled["decisions"]["LITE"] == {
        "outcome": "C3S_LITE_SCREEN_NO_SUPPORT",
        "reasons": ["EE_NOT_STRICTLY_ABOVE_BASE"],
    }
    base_bits = screen._fraction_from_payload(pooled["arms"]["BASE"]["total_bits"])
    assert base_bits == Fraction.from_float(0.1) + Fraction.from_float(0.2)
    no_support = screen.pool_unit_receipts([
        _receipt(
            base=(2.0, 1.0, 100), full=(1.0, 1.0, 99), lite=(3.0, 1.0, 100),
            full_changes=0, lite_changes=0,
        )
    ])
    assert no_support["decisions"]["FULL"]["reasons"] == [
        "EE_NOT_STRICTLY_ABOVE_BASE", "SERVICE_MARGIN_FAILED",
    ]
    assert no_support["decisions"]["LITE"]["outcome"] == "C3S_LITE_SCREEN_SUPPORT"


def test_merge_reports_two_decisions_fixed_progression_and_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    receipts = [
        _receipt(
            base=(2.0, 1.0, 100), full=(3.0, 1.0, 100), lite=(1.0, 1.0, 100),
            full_changes=1, lite_changes=0,
        )
        for _ in range(12)
    ]
    monkeypatch.setattr(
        screen, "_load_complete_units", lambda *_args, **_kwargs: (receipts, [])
    )
    timing = {
        arm: {
            "decisions": 12, "mean_hex": 1.0.hex(), "median_hex": 1.0.hex(),
            "p95_nearest_rank_hex": 1.0.hex(), "maximum_hex": 1.0.hex(),
        }
        for arm in screen.ARMS
    }
    monkeypatch.setattr(screen, "per_arm_wall_timing", lambda _receipts: timing)
    monkeypatch.setattr(
        screen, "coordinator_timing_summary",
        lambda _receipts, *, arm: {"arm": arm, "decisions": 12},
    )
    monkeypatch.setattr(screen, "descriptive_breakdowns", lambda _receipts: {})
    terminal, valid = screen.execute_merge(
        output=tmp_path / "run", horizon=1, preflight_sha256="1" * 64,
        authority_sha256="2" * 64, producer_common_binding={"common": True},
    )
    payload = screen.load_json(terminal, field="terminal")
    assert valid is True
    assert payload["decisions"]["FULL"]["outcome"] == "C3S_FULL_SCREEN_SUPPORT"
    assert payload["decisions"]["LITE"]["outcome"] == "C3S_LITE_SCREEN_NO_SUPPORT"
    assert payload["progression_rule"] == screen.PROGRESSION_RULE
    assert [row["metric"] for row in payload["full_vs_lite_comparison"]] == [
        "eta", "service", "action_changes", "selector_wall_seconds",
    ]


def test_estimate_covers_three_arms_at_t30_and_t100() -> None:
    result = screen.estimate(units=12)
    assert set(result["horizons"]) == {"30", "100"}
    for horizon in result["horizons"].values():
        assert set(horizon["arms"]) == set(screen.ARMS)
        assert horizon["arms"]["FULL"]["worker_hours"] == pytest.approx(
            10 * horizon["arms"]["LITE"]["worker_hours"]
        )


def test_timing_summaries_are_separate_for_all_arms() -> None:
    phases = {
        name: 0.1.hex() for name in (
            "q_inference", "base_nominal_evaluation", "enumeration",
            "remaining_nominal_evaluations", "catalog_total", "selection",
        )
    }

    def decision(catalog: str, wall: float) -> dict[str, object]:
        return {
            "catalog": catalog, "wall_seconds_hex": wall.hex(), "catalog_size": 3,
            "unique_nominal_evaluations": 3, "peak_rss_kib": 10,
            "phase_wall_seconds_hex": phases,
            "profile_counts": {"base": 1, "unilateral": 1, "joint": 1},
        }

    receipt = {
        "decisions_by_arm": {
            "FULL": [decision("full", 3.0)], "LITE": [decision("lite", 1.0)],
        },
        "arms": {
            "BASE": {"decision_wall_seconds_hex": [0.5.hex()]},
            "FULL": {"decision_wall_seconds_hex": [3.0.hex()]},
            "LITE": {"decision_wall_seconds_hex": [1.0.hex()]},
        },
    }
    assert screen.coordinator_timing_summary([receipt], arm="FULL")["decisions"] == 1
    timing = screen.per_arm_wall_timing([receipt])
    assert float.fromhex(timing["BASE"]["maximum_hex"]) == 0.5
    assert float.fromhex(timing["FULL"]["maximum_hex"]) == 3.0
    assert float.fromhex(timing["LITE"]["maximum_hex"]) == 1.0


def test_refuses_unsealed_contract_and_other_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "CONTRACT_PATH", tmp_path / "contract.md")
    with pytest.raises(screen.C3SScreenError, match="not sealed"):
        screen.sealed_contract_binding()
    with pytest.raises(screen.C3SScreenError, match="outside the four"):
        screen.UnitKey(123, screen.LINEAGES[0]).verify()


def test_write_once_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    target = tmp_path / "receipt.json"
    screen.write_once_with_sidecar(target, {"value": 1})
    assert target.stat().st_mode & 0o777 == 0o444
    assert target.with_suffix(".sha256").stat().st_mode & 0o777 == 0o444
    with pytest.raises(screen.C3SScreenError, match="refusing to overwrite"):
        screen.write_once_with_sidecar(target, {"value": 2})


def test_invalid_and_incomplete_semantics() -> None:
    key = screen.ALL_UNITS[0]
    invalid = screen.invalid_receipt(
        scope="unit", error=ValueError("bad"), key=key,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
    )
    incomplete = screen.incomplete_receipt(
        scope="unit", error=KeyboardInterrupt(), key=key,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
    )
    assert (invalid["status"], invalid["integrity"]) == ("INVALID_RUN", False)
    assert (incomplete["status"], incomplete["integrity"]) == ("INCOMPLETE", None)


def test_missing_units_publish_sequenced_incomplete_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    output = tmp_path / "run"
    with pytest.raises(screen.MergeWaiting) as caught:
        screen.execute_merge(
            output=output, horizon=30, preflight_sha256="1" * 64,
            authority_sha256="2" * 64, producer_common_binding={"common": True},
        )
    receipt = caught.value.receipt
    assert receipt == output / "incomplete" / "merge-000001.json"
    assert screen.load_json(receipt, field="incomplete")["status"] == "INCOMPLETE"
    assert receipt.stat().st_mode & 0o777 == 0o444
