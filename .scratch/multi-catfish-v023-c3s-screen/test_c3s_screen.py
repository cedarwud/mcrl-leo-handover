from __future__ import annotations

from contextlib import nullcontext
from copy import deepcopy
import datetime as dt
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import tempfile
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


def readonly(value, dtype=None):
    result = np.asarray(value, dtype=dtype).copy()
    result.setflags(write=False)
    return result


def frozen_candidates(tables) -> c3s_policy.FrozenCandidates:
    users = len(tables)
    return c3s_policy.FrozenCandidates(
        slot_tables=tuple(tables),
        off_axis_deg=readonly(np.zeros((users, 4, 7)), np.float64),
        elevation_deg=readonly(np.ones((users, 4)), np.float64),
        window_satellite_ecef_km=readonly(np.ones((users, 4, 3)), np.float64),
        window_norad_ids=readonly(np.ones((users, 4)), np.int64),
    )


def decision_snapshot(tables, *, catalog="full", q12=None, base=None):
    candidates = frozen_candidates(tables)
    users = len(tables)
    masks = np.stack([table.mask for table in tables])
    keys = np.stack([
        np.stack((table.norad_ids, table.cell_ids), axis=1) for table in tables
    ])
    return c3s_policy.DecisionSnapshot(
        native_state_matrix=readonly(np.zeros((users, 1)), np.float32),
        legal_masks=readonly(masks, np.bool_),
        slot_physical_keys=readonly(keys, np.int64),
        q12_proposal=readonly(
            np.zeros((users, 28), dtype=np.float32) if q12 is None else q12,
            np.float32,
        ),
        base_actions=readonly(
            np.zeros(users, dtype=np.int64) if base is None else base, np.int64
        ),
        candidates=candidates,
        committed_association=tuple(None for _ in range(users)),
        committed_segments=tuple(None for _ in range(users)),
        committed_radiating=None,
        tracking_state=((), ()), interval_s=30.08, catalog=catalog,
        eta_ref=Fraction(1), q_inference_seconds=0.01,
    )


class FakeEvaluator:
    def __init__(self):
        self.calls = []

    def evaluate(self, actions):
        self.calls.append(tuple(np.asarray(actions).tolist()))
        return object()

    def evaluate_many(self, actions):
        return tuple(self.evaluate(action) for action in actions)

    def verify(self):
        return "authenticated-test-evaluator"


def slot_table(keys, legal):
    from mcrl.env.action_contract import SlotTable

    norads = np.full(28, -1, dtype=np.int64)
    cells = np.full(28, -1, dtype=np.int64)
    mask = np.zeros(28, dtype=np.bool_)
    for action, key in enumerate(keys):
        if key is not None:
            norads[action], cells[action] = key
        if action in legal:
            mask[action] = True
    return SlotTable(readonly(norads), readonly(cells), readonly(mask))


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


def test_adapter_inputs_are_capability_free_and_live_state_is_neutral(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = NeutralStepEnv()
    rng = np.random.default_rng(71)
    before_rng = deepcopy(rng.bit_generator.state)
    before = c3s_policy.e1._evaluation_snapshot(environment, rng)
    field = environment._fading_field

    tables = (
        slot_table([(1, 1), (2, 2)], {0, 1}),
        slot_table([(1, 1), (2, 2)], {0, 1}),
    )
    snapshot = decision_snapshot(tables)
    evaluator = FakeEvaluator()
    monkeypatch.setattr(c3s_policy, "_snapshot_inputs", lambda *_args: (snapshot, evaluator))

    def decision(supplied_snapshot, supplied_evaluator):
        c3s_policy._assert_no_prohibited_capabilities(
            (supplied_snapshot, supplied_evaluator)
        )
        assert supplied_snapshot is snapshot
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


def test_full_neutrality_guard_detects_nested_mobility_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = NeutralStepEnv()
    environment._mobility_rng = np.random.default_rng(9)
    rng = np.random.default_rng(71)
    tables = (slot_table([(1, 1)], {0}), slot_table([(1, 1)], {0}))
    snapshot = decision_snapshot(tables)

    def malicious_snapshot(*_args):
        environment._mobility_rng.random()
        return snapshot, FakeEvaluator()

    monkeypatch.setattr(c3s_policy, "_snapshot_inputs", malicious_snapshot)
    adapter = c3s_policy.C3SPolicyAdapter(
        physical=object(), frozen=object(), eta_ref=Fraction(1),
        decision_function=lambda *_args: c3s_policy.DecisionResult(
            actions=np.asarray([0, 0]), base_actions=np.asarray([0, 0]),
            profile_id="BASE", catalog_size=1,
            counts={"base": 1, "unilateral": 0, "joint": 0},
        ),
    )
    with pytest.raises(c3s_policy.C3SPolicyError, match="tracking state"):
        adapter.select_actions(environment, object(), rng)


def test_live_neutrality_guard_does_not_walk_immutable_archive() -> None:
    class ArchiveMustNotBeTraversed:
        @property
        def __dict__(self):
            raise AssertionError("immutable archive was recursively traversed")

    environment = NeutralStepEnv()
    environment.driver.archive = ArchiveMustNotBeTraversed()
    first = c3s_policy._live_neutrality_fingerprint(
        environment, np.random.default_rng(7)
    )
    second = c3s_policy._live_neutrality_fingerprint(
        environment, np.random.default_rng(7)
    )
    assert first == second


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
    tables = (
        slot_table([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], set(range(5))),
        slot_table([(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], set(range(5))),
    )
    kwargs = dict(snapshot=decision_snapshot(tables), evaluator=FakeEvaluator())
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
        slot_table([(1, 1), (2, 2), (1, 1), (3, 3)], {0, 1, 2, 3})
        for _ in range(2)
    )
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
        snapshot=decision_snapshot(tables, q12=q12, catalog="lite"),
        evaluator=FakeEvaluator(),
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
    monkeypatch.setattr(
        screen, "base_q_timing_summary",
        lambda _receipts: {"arm": "BASE", "decisions": 12},
    )
    monkeypatch.setattr(screen, "descriptive_breakdowns", lambda _receipts: {})
    terminal, valid = screen.execute_merge(
        output=tmp_path / "run", horizon=1, preflight_sha256="1" * 64,
        authority_sha256="2" * 64, authority_path=tmp_path / "merge-authority.json",
        producer_common_binding={"common": True},
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
            "remaining_nominal_evaluations", "nominal_evaluation",
            "catalog_total", "selection",
        )
    }

    def decision(catalog: str, wall: float) -> dict[str, object]:
        return {
            "catalog": catalog, "wall_seconds_hex": wall.hex(), "catalog_size": 3,
            "unique_nominal_evaluations": 3, "process_lifetime_peak_rss_kib": 10,
            "rss_measurement_scope": (
                "PROCESS_LIFETIME_HIGH_WATER_MARK_NOT_ISOLATED_PER_ARM;"
                "FULL_EXECUTES_BEFORE_LITE"
            ),
            "phase_wall_seconds_hex": phases,
            "profile_counts": {"base": 1, "unilateral": 1, "joint": 1},
        }

    receipt = {
        "base_decisions": [{
            "wall_seconds_hex": 0.25.hex(),
            "phase_wall_seconds_hex": {
                "q_inference": 0.25.hex(), "enumeration": 0.0.hex(),
                "nominal_evaluation": 0.0.hex(),
            },
            "phase_applicability": {
                "q_inference": "MEASURED",
                "enumeration": "NOT_APPLICABLE_BASE_HAS_NO_CATALOG",
                "nominal_evaluation": "NOT_APPLICABLE_BASE_HAS_NO_NOMINAL_PASS",
            },
            "enumerated_profiles": 0, "unique_nominal_evaluations": 0,
            "selected_nominal": None,
        }],
        "decisions_by_arm": {
            "FULL": [decision("full", 3.0)], "LITE": [decision("lite", 1.0)],
        },
        "arms": {
            "BASE": {"decision_wall_seconds_hex": [0.5.hex()]},
            "FULL": {"decision_wall_seconds_hex": [3.0.hex()]},
            "LITE": {"decision_wall_seconds_hex": [1.0.hex()]},
        },
    }
    summary = screen.coordinator_timing_summary([receipt], arm="FULL")
    assert summary["decisions"] == 1
    assert set(summary["phase_wall_seconds"]) == {
        "q_inference", "enumeration", "nominal_evaluation",
    }
    base_summary = screen.base_q_timing_summary([receipt])
    assert float.fromhex(
        base_summary["phase_wall_seconds"]["q_inference"]["maximum_hex"]
    ) == 0.25
    assert float.fromhex(
        base_summary["phase_wall_seconds"]["enumeration"]["maximum_hex"]
    ) == 0.0
    assert base_summary["phase_applicability"]["nominal_evaluation"].startswith(
        "NOT_APPLICABLE"
    )
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
            authority_sha256="2" * 64, authority_path=tmp_path / "merge-authority.json",
            producer_common_binding={"common": True},
        )
    receipt = caught.value.receipt
    assert receipt == output / "incomplete" / "merge-000001.json"
    assert screen.load_json(receipt, field="incomplete")["status"] == "INCOMPLETE"
    assert receipt.stat().st_mode & 0o777 == 0o444


def native_four_user_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[object, object, c3s_policy.DecisionSnapshot, c3s_policy.NominalSnapshotEvaluator, np.ndarray, np.random.Generator]:
    from mcrl.env.action_contract import NO_OP_ACTION
    from mcrl.env.constants import TLE_ROOT_DEFAULT
    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.env.tle import TleArchive

    archive = Path(TLE_ROOT_DEFAULT).expanduser()
    if not archive.is_dir():
        pytest.skip("canonical TLE archive is unavailable")
    environment = StepEnvironment(
        ScenarioDriver(
            TleArchive(archive),
            ScenarioConfig(mobility=MobilityConfig(num_users=4)),
        ),
        fading_field=KeyedFadingField.from_components("c3s-detached-test", 1, 4),
    )
    rng = np.random.default_rng(2026090801)
    mobility_rng = np.random.default_rng(2026090802)
    observation = environment.reset(
        dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc),
        rng,
        mobility_rng=mobility_rng,
    )
    base = np.full(4, NO_OP_ACTION, dtype=np.int64)
    for user, mask in enumerate(observation.masks):
        legal = np.flatnonzero(mask)
        if legal.size:
            base[user] = int(legal[0])
    native = SimpleNamespace(
        state_matrix=readonly(observation.state_matrix, np.float32),
        action_masks=readonly(observation.masks, np.bool_),
        verify=lambda: "verified",
    )
    q12 = np.zeros((4, 28), dtype=np.float32)
    monkeypatch.setattr(
        c3s_policy.e1, "_q12_surface_base_only",
        lambda *_args: (native, q12, base),
    )
    # The native E1 metric helper is panel-sized; retain its real computation
    # while authorizing this four-user regression fixture.
    monkeypatch.setattr(c3s_policy.e1, "USERS", 4)
    adapter = c3s_policy.C3SPolicyAdapter(
        physical=object(), frozen=object(), eta_ref=Fraction(1),
    )
    snapshot, evaluator = c3s_policy._snapshot_inputs(
        adapter, environment, observation
    )
    return environment, observation, snapshot, evaluator, base, rng


def test_detached_evaluator_matches_native_nominal_physics_and_is_pure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment, _observation, snapshot, evaluator, base, rng = native_four_user_snapshot(
        monkeypatch
    )
    c3s_policy._assert_no_prohibited_capabilities((snapshot, evaluator))
    live_before = c3s_policy._live_neutrality_fingerprint(environment, rng)
    with c3s_policy.s0.nominal_no_fading(environment):
        live = c3s_policy.e1._evaluate_actions_neutral(environment, base, rng)
    detached_first = evaluator.evaluate(base)
    detached_second = evaluator.evaluate(base)
    assert np.array_equal(detached_first.link_rate_bps, live.link_rate_bps)
    assert np.array_equal(detached_first.link_power_w, live.link_power_w)
    assert detached_first.system_power_w == live.system_power_w
    assert np.array_equal(detached_first.link_rate_bps, detached_second.link_rate_bps)
    assert c3s_policy._live_neutrality_fingerprint(environment, rng) == live_before


def test_actual_evacuation_membership_common_destinations_and_order() -> None:
    tables = (
        slot_table([(10, 1), (20, 2), (30, 3)], {0, 1, 2}),
        slot_table([(10, 1), (20, 2)], {0, 1}),
        slot_table([(5, 4), (20, 2)], {0, 1}),
    )
    observation = SimpleNamespace(
        candidates=SimpleNamespace(slot_tables=tables)
    )
    profile = SimpleNamespace(
        users=3,
        served=np.asarray([True, True, True]),
        serving_satellite=np.asarray([10, 10, 5]),
        serving_cell=np.asarray([1, 1, 4]),
    )
    rows = c3s_policy._evacuation_skeletons(
        observation, np.asarray([0, 0, 0]), profile
    )
    assert [row["profile_id"] for row in rows] == [
        "J:5:4->20:2", "J:10:1->20:2",
    ]
    assert rows[0]["actions"].tolist() == [0, 0, 1]
    assert rows[1]["actions"].tolist() == [1, 1, 0]


def test_actual_catalog_retains_aliases_and_memoizes_identical_vectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    table = slot_table([(10, 1), (20, 2)], {0, 1})
    snapshot = decision_snapshot((table,))
    profile = SimpleNamespace(
        users=1, served=np.asarray([True]),
        serving_satellite=np.asarray([10]), serving_cell=np.asarray([1]),
    )
    evaluator = FakeEvaluator()
    monkeypatch.setattr(
        c3s_policy.f1, "profile_from_evaluation",
        lambda *_args, **_kwargs: (profile, np.zeros(1)),
    )
    monkeypatch.setattr(
        c3s_policy.e1, "_profile_metrics",
        lambda *_args: {
            "total_bits": 10.0.hex(), "total_energy_j": 2.0.hex(),
            "served": 1, "opportunities": 1,
        },
    )
    rows = c3s_policy.build_s0_catalog(snapshot=snapshot, evaluator=evaluator)
    assert [row["profile_id"] for row in rows] == [
        "BASE", "U:0:1", "J:10:1->20:2",
    ]
    assert rows[1]["actions"].tolist() == rows[2]["actions"].tolist() == [1]
    assert evaluator.calls == [(0,), (1,)]


def test_real_selection_is_repeatable_from_one_frozen_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _environment, _observation, snapshot, evaluator, _base, _rng = (
        native_four_user_snapshot(monkeypatch)
    )
    before = snapshot.verify()
    evaluator_before = evaluator.verify()
    first = c3s_policy._real_decision(snapshot, evaluator)
    second = c3s_policy._real_decision(snapshot, evaluator)
    assert (
        first.profile_id, first.actions.tolist(), first.nominal,
        first.catalog_size, first.counts, first.unique_nominal_evaluations,
    ) == (
        second.profile_id, second.actions.tolist(), second.nominal,
        second.catalog_size, second.counts, second.unique_nominal_evaluations,
    )
    assert snapshot.verify() == before
    assert evaluator.verify() == evaluator_before


def test_process_pool_reduces_in_canonical_order_and_matches_serial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _environment, _observation, snapshot, evaluator, _base, _rng = (
        native_four_user_snapshot(monkeypatch)
    )
    serial = c3s_policy._real_decision(snapshot, evaluator)
    with c3s_policy.ProcessPoolExecutor(
        max_workers=2,
        mp_context=c3s_policy.multiprocessing.get_context("fork"),
    ) as executor:
        parallel = c3s_policy._real_decision(
            snapshot, evaluator, executor=executor, evaluation_workers=2
        )
    assert (
        parallel.profile_id, parallel.actions.tolist(), parallel.nominal,
        parallel.catalog_size, parallel.counts, parallel.unique_nominal_evaluations,
    ) == (
        serial.profile_id, serial.actions.tolist(), serial.nominal,
        serial.catalog_size, serial.counts, serial.unique_nominal_evaluations,
    )


def test_lite_worker_cli_defaults_to_sealed_single_process_path() -> None:
    assert screen._parser().parse_args([]).lite_workers == 1
    assert screen._parser().parse_args(["--lite-workers", "8"]).lite_workers == 8


def test_adapter_refuses_reviewer_reproduced_evaluator_geometry_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment, observation, snapshot, evaluator, base, rng = native_four_user_snapshot(
        monkeypatch
    )
    snapshot_digest = snapshot.verify()

    def mutate_geometry(supplied_snapshot, supplied_evaluator):
        supplied_evaluator.snapshot.user_ecef_km.setflags(write=True)
        supplied_evaluator.snapshot.user_ecef_km[0, 0] += 100.0
        assert supplied_snapshot.verify() == snapshot_digest
        return c3s_policy.DecisionResult(
            actions=base, base_actions=base, profile_id="BASE", catalog_size=1,
            counts={"base": 1, "unilateral": 0, "joint": 0},
        )

    adapter = c3s_policy.C3SPolicyAdapter(
        physical=object(), frozen=object(), eta_ref=Fraction(1),
        decision_function=mutate_geometry,
    )
    monkeypatch.setattr(
        c3s_policy, "_snapshot_inputs", lambda *_args: (snapshot, evaluator)
    )
    with pytest.raises(c3s_policy.C3SPolicyError, match="geometry/physics"):
        adapter.select_actions(environment, observation, rng)


def test_adapter_refuses_rng_child_spawning_inside_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    environment = NeutralStepEnv()
    rng = np.random.default_rng(71)
    tables = (slot_table([(1, 1)], {0}), slot_table([(1, 1)], {0}))
    snapshot = decision_snapshot(tables)
    evaluator = FakeEvaluator()
    monkeypatch.setattr(
        c3s_policy, "_snapshot_inputs", lambda *_args: (snapshot, evaluator)
    )

    def spawn_rng(*_args):
        rng.spawn(1)
        return c3s_policy.DecisionResult(
            actions=np.asarray([0, 0]), base_actions=np.asarray([0, 0]),
            profile_id="BASE", catalog_size=1,
            counts={"base": 1, "unilateral": 0, "joint": 0},
        )

    adapter = c3s_policy.C3SPolicyAdapter(
        physical=object(), frozen=object(), eta_ref=Fraction(1),
        decision_function=spawn_rng,
    )
    with pytest.raises(c3s_policy.C3SPolicyError, match="environment/RNG"):
        adapter.select_actions(environment, object(), rng)


def test_actual_catalog_rejects_duplicate_physical_keys_and_accepts_empty_noop() -> None:
    duplicate = slot_table([(10, 1), (20, 2), (20, 2)], {0, 1, 2})
    observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=(duplicate,)))
    with pytest.raises(Exception, match="alias one candidate physical configuration"):
        c3s_policy.f1.enumerate_unilateral_candidates(observation, np.asarray([0]))

    empty = slot_table([], set())
    empty_observation = SimpleNamespace(candidates=SimpleNamespace(slot_tables=(empty,)))
    assert c3s_policy.f1.enumerate_unilateral_candidates(
        empty_observation, np.asarray([c3s_policy.f1.NO_OP_ACTION])
    ) == ()
    assert c3s_policy._lite_unilateral_skeletons(
        empty_observation,
        np.asarray([c3s_policy.f1.NO_OP_ACTION]),
        np.zeros((1, 28), dtype=np.float32),
    ) == ()


def test_completed_unit_is_authenticated_and_reused_before_physics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    screen.pin_single_thread_runtime()
    monkeypatch.setattr(screen, "HERE", tmp_path)
    contract = tmp_path / "contract.md"
    contract.write_text("sealed test contract\n", encoding="ascii")
    contract_digest = screen.file_sha256(contract)
    Path(f"{contract}.sha256").write_text(
        f"{contract_digest}  {contract.name}\n", encoding="ascii"
    )
    contract.chmod(0o444)
    Path(f"{contract}.sha256").chmod(0o444)
    monkeypatch.setattr(screen, "CONTRACT_PATH", contract)
    key = screen.ALL_UNITS[0]
    output = tmp_path / "run"
    preflight = tmp_path / "preflight.json"
    preflight.write_text("{}\n", encoding="ascii")
    preflight_sha = screen.file_sha256(preflight)
    authority_path = tmp_path / "authority.json"
    arguments = [
        "--unit", f"{key.world}:{key.lineage}",
        "--preflight-manifest", str(preflight),
        "--launch-authority", str(authority_path),
        "--output", str(output), "--horizon", "30",
    ]
    static = screen.validate_static_bindings()
    authority = {
        "schema": screen.LAUNCH_AUTHORITY_SCHEMA,
        "status": "FROZEN_LAUNCH_AUTHORITY",
        "claim_ceiling": screen.CLAIM_CEILING,
        "contract": static["contract"],
        "preflight_manifest": {"path": str(preflight), "sha256": preflight_sha},
        "lineage_authorities": static["lineage_authorities"],
        "preregistration": static["preregistration"],
        "tle_archive": static["tle_archive"],
        "code_files": screen.expected_code_bindings(),
        "freeze_provenance": {
            "evidence_manifest": None, "world_census": None, "freeze": None,
        },
        "execution": {
            "mode": "unit", "unit": key.as_dict(),
            "panel": screen.panel_bindings(30),
            "eta_ref_exact": screen.fraction_payload(
                screen.c3s_policy.load_eta_ref(screen.CONFIG_PATH)
            ),
        },
        "output_root": str(output), "launch_arguments": arguments,
        "test_split_opened": False, "episode_training": False,
        "learner_update": False, "efficacy_claim": False,
    }
    _authority, _sidecar, authority_sha = screen.write_once_with_sidecar(
        authority_path, authority
    )
    common = screen.authority_common_binding(authority)
    steps = [{
        "step_index": index, "bits_hex": 1.0.hex(), "energy_j_hex": 1.0.hex(),
        "served": screen.USERS, "opportunities": screen.USERS,
    } for index in range(30)]
    trajectory = {
        "initial_state_sha256": "a" * 64, "action_trace_sha256": "b" * 64,
        "decision_wall_seconds_hex": [0.0.hex()] * 30, "steps": steps,
    }
    base_record = {
        "wall_seconds_hex": 0.0.hex(),
        "phase_wall_seconds_hex": {
            "q_inference": 0.0.hex(), "enumeration": 0.0.hex(),
            "nominal_evaluation": 0.0.hex(),
        },
        "phase_applicability": {
            "q_inference": "MEASURED",
            "enumeration": "NOT_APPLICABLE_BASE_HAS_NO_CATALOG",
            "nominal_evaluation": "NOT_APPLICABLE_BASE_HAS_NO_NOMINAL_PASS",
        },
        "enumerated_profiles": 0, "unique_nominal_evaluations": 0,
        "selected_nominal": None,
    }
    receipt = {
        "schema": screen.UNIT_RECEIPT_SCHEMA, "status": "COMPLETE",
        "outcome": "C3S_SCREEN_UNIT_COMPLETE", "claim_ceiling": screen.CLAIM_CEILING,
        "unit": key.as_dict(), "horizon": 30, "users": screen.USERS,
        "field_component": screen.FIELD_COMPONENT,
        "field_root_digest": screen.e1.KeyedFadingField.from_components(
            screen.FIELD_COMPONENT, key.world
        ).root_digest,
        "lineage_authority": screen.f2.lineage_authority_bindings()[0],
        "eta_ref_exact": screen.fraction_payload(screen.c3s_policy.load_eta_ref()),
        "arms": {arm: deepcopy(trajectory) for arm in screen.ARMS},
        "base_decisions": [deepcopy(base_record) for _ in range(30)],
        "decisions_by_arm": {
            arm: [{"action_changed": False} for _ in range(30)]
            for arm in screen.COORDINATOR_ARMS
        },
        "action_changes_by_arm": {arm: 0 for arm in screen.COORDINATOR_ARMS},
        "preflight_manifest_sha256": preflight_sha,
        "launch_authority_sha256": authority_sha,
        "launch_authority": {"path": str(authority_path), "sha256": authority_sha},
        "producer_common_binding": common,
        "integrity": True, "test_split_opened": False,
        "episode_training": False, "learner_update": False, "efficacy_claim": False,
    }
    existing = screen._publish_unit(output, key, receipt)
    class PhysicsSentinel:
        def __call__(self, *_args, **_kwargs):
            pytest.fail("completed unit was recomputed")

    PhysicsSentinel.__module__ = "builtins"
    monkeypatch.setattr(screen, "execute_physical_unit", PhysicsSentinel())
    path, valid = screen.execute_unit(
        key=key, output=output, horizon=30,
        preflight_sha256=preflight_sha, authority_sha256=authority_sha,
        authority_path=authority_path, producer_common_binding=common,
    )
    assert (path, valid) == (existing, True)


@pytest.mark.parametrize("failure", [KeyboardInterrupt(), MemoryError()])
def test_interruption_and_resource_failure_publish_retryable_attempts(
    failure: BaseException, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    key = screen.ALL_UNITS[0]
    output = tmp_path / "run"
    monkeypatch.setattr(
        screen, "execute_physical_unit",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(failure),
    )
    attempt, valid = screen.execute_unit(
        key=key, output=output, horizon=30,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
        authority_path=tmp_path / "authority.json",
        producer_common_binding={"common": True},
    )
    assert valid is False
    assert screen.load_json(attempt, field="attempt")["status"] == "INCOMPLETE"
    assert not screen._unit_path(output, key).exists()

    monkeypatch.setattr(
        screen, "execute_physical_unit",
        lambda *_args, **_kwargs: {"schema": screen.UNIT_RECEIPT_SCHEMA},
    )
    canonical, retried = screen.execute_unit(
        key=key, output=output, horizon=30,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
        authority_path=tmp_path / "authority.json",
        producer_common_binding={"common": True},
    )
    assert retried is True
    assert canonical == screen._unit_path(output, key)


def test_bogus_producer_authority_digest_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    authority = tmp_path / "authority.json"
    authority.write_text("{}\n", encoding="ascii")
    receipt = {
        "launch_authority": {"path": str(authority), "sha256": "0" * 64},
    }
    with pytest.raises(screen.C3SScreenError, match="authority digest is invalid"):
        screen._producer_authority(
            receipt, key=screen.ALL_UNITS[0], root=tmp_path / "run", horizon=30,
            preflight_sha256="1" * 64,
            producer_common_binding={"preflight_manifest": {}},
        )


def test_atomic_terminal_publication_recovers_after_interrupted_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    original_rename = screen.os.rename

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(screen.os, "rename", interrupt)
    with pytest.raises(KeyboardInterrupt):
        screen._publish_directory_artifact(
            tmp_path / "run", directory_name=screen.TERMINAL_DIRECTORY_NAME,
            filename=screen.TERMINAL_RECEIPT_NAME, payload={"status": "COMPLETE"},
        )
    terminal = (
        tmp_path / "run" / screen.TERMINAL_DIRECTORY_NAME
        / screen.TERMINAL_RECEIPT_NAME
    )
    assert not terminal.exists()

    monkeypatch.setattr(screen.os, "rename", original_rename)
    published = screen._publish_directory_artifact(
        tmp_path / "run", directory_name=screen.TERMINAL_DIRECTORY_NAME,
        filename=screen.TERMINAL_RECEIPT_NAME, payload={"status": "COMPLETE"},
    )
    assert published == terminal


def test_terminal_and_global_invalidation_reentry_do_not_execute_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    common = {"common": True}
    terminal_payload = {
        "schema": screen.TERMINAL_RECEIPT_SCHEMA,
        "status": "COMPLETE", "outcome": "C3S_THREE_ARM_SCREEN_COMPLETE",
        "preflight_manifest_sha256": "1" * 64,
        "launch_authority_sha256": "2" * 64,
        "launch_authority": {
            "path": str((tmp_path / "merge-authority.json").resolve()),
            "sha256": "2" * 64,
        },
        "producer_common_binding": common, "integrity": True,
    }
    terminal = screen._publish_directory_artifact(
        tmp_path / "complete-run", directory_name=screen.TERMINAL_DIRECTORY_NAME,
        filename=screen.TERMINAL_RECEIPT_NAME, payload=terminal_payload,
    )
    monkeypatch.setattr(
        screen, "_load_complete_units",
        lambda *_args, **_kwargs: pytest.fail("terminal reentry executed merge"),
    )
    assert screen.execute_merge(
        output=tmp_path / "complete-run", horizon=30,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
        authority_path=tmp_path / "merge-authority.json",
        producer_common_binding=common,
    ) == (terminal, True)

    invalid_payload = {
        "schema": screen.TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN", "outcome": "INVALID_RUN", "scope": "merge",
        "preflight_manifest_sha256": "1" * 64,
        "launch_authority_sha256": "2" * 64,
        "launch_authority": {
            "path": str((tmp_path / "merge-authority.json").resolve()),
            "sha256": "2" * 64,
        },
        "producer_common_binding": common, "integrity": False,
    }
    invalidation = screen._publish_directory_artifact(
        tmp_path / "invalid-run",
        directory_name=screen.GLOBAL_INVALIDATION_DIRECTORY_NAME,
        filename=screen.GLOBAL_INVALIDATION_NAME, payload=invalid_payload,
    )
    assert screen.execute_merge(
        output=tmp_path / "invalid-run", horizon=30,
        preflight_sha256="1" * 64, authority_sha256="2" * 64,
        authority_path=tmp_path / "merge-authority.json",
        producer_common_binding=common,
    ) == (invalidation, False)


def test_unit_observes_global_invalidation_before_physics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(screen, "HERE", tmp_path)
    common = {"common": True}
    authority_path = tmp_path / "merge-authority.json"
    payload = {
        "schema": screen.TERMINAL_RECEIPT_SCHEMA,
        "status": "INVALID_RUN", "outcome": "INVALID_RUN", "scope": "merge",
        "preflight_manifest_sha256": "1" * 64,
        "launch_authority_sha256": "2" * 64,
        "launch_authority": {"path": str(authority_path), "sha256": "2" * 64},
        "producer_common_binding": common, "integrity": False,
    }
    invalidation = screen._publish_directory_artifact(
        tmp_path / "run", directory_name=screen.GLOBAL_INVALIDATION_DIRECTORY_NAME,
        filename=screen.GLOBAL_INVALIDATION_NAME, payload=payload,
    )
    monkeypatch.setattr(
        screen, "execute_physical_unit",
        lambda *_args, **_kwargs: pytest.fail("global invalidation reached physics"),
    )
    assert screen.execute_unit(
        key=screen.ALL_UNITS[0], output=tmp_path / "run", horizon=30,
        preflight_sha256="1" * 64, authority_sha256="3" * 64,
        authority_path=tmp_path / "unit-authority.json",
        producer_common_binding=common,
    ) == (invalidation, False)


def test_competing_merge_reuses_complete_and_never_publishes_invalidation(
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
    monkeypatch.setattr(
        screen, "base_q_timing_summary",
        lambda _receipts: {"arm": "BASE", "decisions": 12},
    )
    monkeypatch.setattr(screen, "descriptive_breakdowns", lambda _receipts: {})
    original_publish = screen._publish_directory_artifact
    publications: list[str] = []

    def competing_publish(root, *, directory_name, filename, payload):
        publications.append(directory_name)
        published = original_publish(
            root, directory_name=directory_name, filename=filename, payload=payload
        )
        if directory_name == screen.TERMINAL_DIRECTORY_NAME:
            raise screen.C3SScreenError("simulated competing terminal collision")
        return published

    monkeypatch.setattr(screen, "_publish_directory_artifact", competing_publish)
    terminal, valid = screen.execute_merge(
        output=tmp_path / "run", horizon=1, preflight_sha256="1" * 64,
        authority_sha256="2" * 64, authority_path=tmp_path / "merge-authority.json",
        producer_common_binding={"common": True},
    )
    assert valid is True
    assert terminal.name == screen.TERMINAL_RECEIPT_NAME
    assert publications == [screen.TERMINAL_DIRECTORY_NAME]
    assert not (tmp_path / "run" / screen.GLOBAL_INVALIDATION_DIRECTORY_NAME).exists()


def test_freeze_binds_ops3_native_state_f0_and_all_physics_sources() -> None:
    bindings = screen.expected_code_bindings()
    paths = {Path(row["path"]).name for row in bindings}
    assert {
        "ee_axis_ops3_live.py", "ee_axis_state.py", "c3_contingency_f0.py",
        "step.py", "energy_efficiency.py", "interference.py", "link_budget.py",
        "run_v020_repriced_c3_gate.py",
    }.issubset(paths)
    assert set(screen._inference_hand_list()).issubset(screen.actual_import_graph_paths())


def test_import_graph_census_refuses_omitted_q_head_loader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loader = Path(screen.f2.v020_loader.__file__).resolve()
    graph = tuple(path for path in screen.actual_import_graph_paths() if path != loader)
    monkeypatch.setattr(screen, "actual_import_graph_paths", lambda: graph)
    with pytest.raises(screen.C3SScreenError, match="omits hand-listed"):
        screen.expected_code_bindings()


def test_complete_world_census_rejects_incomplete_or_unrelated_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = screen.derive_world_inventory()
    source = tmp_path / "inventory.json"
    source.write_text("{}\n", encoding="ascii")
    payload = {
        "schema": screen.WORLD_CENSUS_SCHEMA,
        "status": "FROZEN_COMPLETE_USED_ALLOCATED_CENSUS",
        "inventory_complete": True,
        "inventory_scope": "all project used and allocated world authorities",
        "source_artifacts": [{"path": str(source), "sha256": screen.file_sha256(source)}],
        "used_worlds": [], "allocated_worlds": [],
        "c3s_worlds": list(screen.WORLDS), "collisions": [],
    }
    monkeypatch.setattr(
        screen, "_sealed_json_binding",
        lambda *_args, **_kwargs: (payload, {"path": "x", "sha256": "1" * 64}),
    )
    with pytest.raises(screen.C3SScreenError, match="does not cover"):
        screen.validate_world_census({})

    payload["source_artifacts"] = expected["source_artifacts"]
    payload["used_worlds"] = expected["used_worlds"]
    payload["allocated_worlds"] = expected["allocated_worlds"]
    assert screen.validate_world_census({}) == {"path": "x", "sha256": "1" * 64}
    payload["used_worlds"] = [*expected["used_worlds"], screen.WORLDS[0]]
    with pytest.raises(screen.C3SScreenError, match="malformed"):
        screen.validate_world_census({})


@pytest.mark.skipif(
    os.environ.get("C3S_RUN_ARCHIVED_EQUIVALENCE") != "1",
    reason="set C3S_RUN_ARCHIVED_EQUIVALENCE=1 for the physical archived replay",
)
def test_archived_lite_replay_equivalence_and_receipt_determinism() -> None:
    """Replay two v1 units through serial and pooled LITE for five steps."""

    from mcrl.env.keyed_fading import KeyedFadingField
    from mcrl.runtime.prereg import read_prereg
    from mcrl.runtime.training_pipeline import _evaluation_rngs

    receipt_root = Path(os.environ.get(
        "C3S_ARCHIVED_RECEIPTS",
        "/home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/"
        "runs/c3s-20260908-r1/units",
    ))
    units = (
        screen.UnitKey(8464287092499831892, 2026092101),
        screen.UnitKey(7305539127129390835, 2026092102),
    )
    record = read_prereg(screen.f1.PREREG_PATH)
    physical, server = screen.f1._runtime_modules()

    def run_variant(archive, frozen, key, *, workers: int):
        environment = screen._make_environment(archive, horizon=30)
        environment.environment._fading_field = KeyedFadingField.from_components(
            screen.FIELD_COMPONENT, key.world
        )
        rngs = tuple(_evaluation_rngs(key.world))
        _states, _masks, observation = environment.reset(rngs[0], rngs[1])
        adapter = c3s_policy.C3SPolicyAdapter(
            physical=physical, frozen=frozen, catalog="lite",
            evaluation_workers=workers,
        )
        rows = []
        try:
            for step_index in range(5):
                actions = adapter.select_actions(
                    environment.environment, observation, rngs[0]
                )
                environment.step(actions, rngs[0])
                outcome = environment.last_outcome
                decision = adapter.decision_records[-1]
                realised = screen._step_metric(
                    outcome,
                    float(environment.environment.driver.config.ephemeris.time_step_s),
                )
                rows.append({
                    "step_index": step_index,
                    "profile_id": decision["selected_profile_id"],
                    "actions": actions.tolist(),
                    "nominal": decision["selected_nominal"],
                    "realised": realised,
                })
                observation = outcome.observation
        finally:
            adapter.close()
        digest = hashlib.sha256(screen.canonical_bytes(rows)).hexdigest()
        return rows, digest

    for key in units:
        archived = json.loads(
            (receipt_root / key.slug / screen.UNIT_RECEIPT_NAME).read_text(
                encoding="ascii"
            )
        )
        frozen = screen.f2._load_frozen_heads(key.lineage)
        with tempfile.TemporaryDirectory(prefix=f"c3s-equivalence-{key.slug}-") as tmp:
            archive = server._freeze_archive(
                record, screen.CANONICAL_TLE_ROOT, Path(tmp) / "frozen", physical
            )
            serial, _serial_digest = run_variant(
                archive, frozen, key, workers=1
            )
            pooled_first, first_digest = run_variant(
                archive, frozen, key, workers=8
            )
            pooled_second, second_digest = run_variant(
                archive, frozen, key, workers=8
            )
        assert pooled_first == serial
        assert pooled_second == pooled_first
        assert second_digest == first_digest
        for index, row in enumerate(pooled_first):
            archived_decision = archived["decisions_by_arm"]["LITE"][index]
            archived_outcome = archived["arms"]["LITE"]["steps"][index]
            assert row["profile_id"] == archived_decision["selected_profile_id"]
            assert row["nominal"] == archived_decision["selected_nominal"]
            assert row["realised"] == {
                name: value for name, value in archived_outcome.items()
                if name != "step_index"
            }
