from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import c3s_diagnostic_policy as policy
import c3s_physics_override as physics_override
import run_v023_c3s_diagnostic_arms as runner


def metric(bits: float, energy: float, served: int) -> dict[str, object]:
    return {
        "total_bits": bits, "total_energy_j": energy,
        "served": served, "opportunities": 3,
    }


def candidate(profile_id: str, kind: str, action: int, *, bits: float, served: int):
    return {
        "profile_id": profile_id, "kind": kind,
        "actions": np.asarray([action], dtype=np.int64),
        "nominal": metric(bits, 1.0, served),
    }


def test_random_feasible_respects_nominal_service_guard() -> None:
    catalog = (
        candidate("BASE", "base", 0, bits=1.0, served=2),
        candidate("U:0:1", "unilateral", 1, bits=100.0, served=1),
        candidate("U:0:2", "unilateral", 2, bits=2.0, served=2),
    )
    for step in range(100):
        selected = policy.random_feasible_candidate(
            catalog, domain=f"C3S_DIAG/random/7/8/{step}",
        )
        assert selected["nominal"]["served"] >= 2
        assert selected["profile_id"] != "U:0:1"


def test_catalog_restrictions_are_exact() -> None:
    catalog = (
        candidate("BASE", "base", 0, bits=1.0, served=3),
        candidate("U:0:1", "unilateral", 1, bits=2.0, served=3),
        candidate("J:1:2->3:4", "joint", 2, bits=3.0, served=3),
    )
    unilateral = policy.restricted_catalog(catalog, keep="unilateral")
    evacuation = policy.restricted_catalog(catalog, keep="joint")
    assert [row["profile_id"] for row in unilateral] == ["BASE", "U:0:1"]
    assert [row["profile_id"] for row in evacuation] == ["BASE", "J:1:2->3:4"]
    assert {row["kind"] for row in unilateral} == {"base", "unilateral"}
    assert {row["kind"] for row in evacuation} == {"base", "joint"}


def test_null_exercises_catalog_score_and_guard_but_executes_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = (
        candidate("BASE", "base", 0, bits=1.0, served=3),
        candidate("U:0:1", "unilateral", 1, bits=5.0, served=3),
    )
    calls = {"catalog": 0, "selection": 0}

    def build(**kwargs):
        calls["catalog"] += 1
        kwargs["timing_out"].update({
            "base_nominal_evaluation": 0.0, "enumeration": 0.0,
            "remaining_nominal_evaluations": 0.0, "nominal_evaluation": 0.0,
            "unique_nominal_evaluations": 2.0,
        })
        return catalog

    def select(rows, *, eta_ref):
        calls["selection"] += 1
        assert rows is catalog and eta_ref == Fraction(1)
        return catalog[1]

    monkeypatch.setattr(policy.c3s_policy, "build_s0_catalog", build)
    monkeypatch.setattr(policy.c3s_policy, "select_candidate", select)
    snapshot = SimpleNamespace(q_inference_seconds=0.0, eta_ref=Fraction(1), base_actions=np.asarray([0]))
    result = policy.learned_decision(
        snapshot, object(), arm="NULL", world=1, lineage=2, step=0,
    )
    assert calls == {"catalog": 1, "selection": 1}
    assert result.profile_id == "BASE"
    assert result.actions.tolist() == [0]


def test_heur_is_q_free(monkeypatch: pytest.MonkeyPatch) -> None:
    environment = SimpleNamespace(marker=1)
    observation = object()
    expected = np.zeros(runner.USERS, dtype=np.int64)
    monkeypatch.setattr(policy.c3s_policy, "_structural_sha256", lambda value: str(value.marker))
    monkeypatch.setattr(policy, "nominal_local_snr_actions", lambda *_args: expected)
    selector = policy.QFreeSelector(arm="HEUR")
    result = selector.select_actions(environment, observation, np.random.default_rng(1))
    assert np.array_equal(result, expected)
    assert selector.q_head_accesses == 0
    assert not hasattr(selector, "physical") and not hasattr(selector, "frozen")
    assert len(selector.decision_records) == 1
    assert selector.decision_records[0]["q_head_accesses"] == 0
    assert selector.decision_records[0]["information_rule"] == "NO_Q_HEADS_NO_LEARNED_PROPOSALS"


class Observation:
    def __init__(self, step: int) -> None:
        self.step_index = step
        self.masks = np.ones((runner.USERS, runner.donor.f1.NUM_ACTIONS), dtype=np.bool_)
        tables = tuple(SimpleNamespace(
            mask=self.masks[uid],
            norad_ids=np.arange(runner.donor.f1.NUM_ACTIONS, dtype=np.int64) + 100,
            cell_ids=np.arange(runner.donor.f1.NUM_ACTIONS, dtype=np.int64) + uid,
        ) for uid in range(runner.USERS))
        self.candidates = SimpleNamespace(
            slot_tables=tables,
            dwell=SimpleNamespace(phase=float(step % 4) / 4.0),
        )


class ThreeStepWorld:
    def __init__(self) -> None:
        self.position = 0
        self.index = 0
        self.environment = self
        self.driver = SimpleNamespace(config=SimpleNamespace(
            ephemeris=SimpleNamespace(time_step_s=1.0)
        ))
        self._segments = [None] * runner.USERS
        self._pending_segment_age = None
        self._step_index = 0
        self.last_outcome = None

    def reset(self, _env_rng, _mobility_rng):
        self.position = 0
        self.index = 0
        self._step_index = 0
        self._segments = [None] * runner.USERS
        return [], [], Observation(0)

    def step(self, actions, _rng):
        step = self.index
        self.position += int(actions[0]) + 1
        self._segments = [SimpleNamespace(age_steps=step + 1)] * runner.USERS
        done = step == 2
        self.last_outcome = SimpleNamespace(
            link_rate_bps=np.full(runner.USERS, float(self.position)),
            system_power_w=float(self.position + 2),
            link_power_w=np.full(runner.USERS, 0.825),
            radiating=SimpleNamespace(count=7 + step),
            handovers=tuple(SimpleNamespace(value="none") for _ in range(runner.USERS)),
            resolution=SimpleNamespace(
                served_count=runner.USERS,
                served=np.ones(runner.USERS, dtype=np.bool_),
                serving_satellite=np.full(runner.USERS, 100, dtype=np.int64),
                serving_cell=np.arange(runner.USERS, dtype=np.int64),
            ),
            done=done, observation=Observation(step + 1),
        )
        self.index = step + 1
        self._step_index = self.index
        return SimpleNamespace(done=done)


def test_null_equals_base_on_synthetic_three_step_world(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mcrl.runtime.ee_axis_state as state_module

    monkeypatch.setattr(
        state_module, "encode_ee_axis_state",
        lambda *_args: SimpleNamespace(state_sha256="a" * 64),
    )
    actions = np.zeros(runner.USERS, dtype=np.int64)
    base = runner.run_arm_trajectory(
        environment=ThreeStepWorld(), env_rng=np.random.default_rng(11),
        mobility_rng=np.random.default_rng(12), horizon=3,
        selector=lambda *_args: actions,
    )
    null = runner.run_arm_trajectory(
        environment=ThreeStepWorld(), env_rng=np.random.default_rng(11),
        mobility_rng=np.random.default_rng(12), horizon=3,
        selector=lambda *_args: actions,
    )
    runner.assert_null_equals_base({"BASE": base, "NULL": null})
    null["steps"][1]["served"] -= 1
    with pytest.raises(runner.DiagnosticRunnerError, match="step 1"):
        runner.assert_null_equals_base({"BASE": base, "NULL": null})


def test_shuffled_score_is_seeded_and_guarded() -> None:
    catalog = (
        candidate("BASE", "base", 0, bits=1.0, served=2),
        candidate("U:0:1", "unilateral", 1, bits=100.0, served=1),
        candidate("U:0:2", "unilateral", 2, bits=3.0, served=2),
    )
    domain = "C3S_DIAG/shuffle/1/2/3"
    first = policy.shuffled_score_candidate(catalog, eta_ref=Fraction(1), domain=domain)
    second = policy.shuffled_score_candidate(catalog, eta_ref=Fraction(1), domain=domain)
    assert first["profile_id"] == second["profile_id"]
    assert first["nominal"]["served"] >= 2


def test_heur_lite_ranks_one_alternative_per_user_by_nominal_f(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = (
        candidate("BASE", "base", 0, bits=1.0, served=3),
        candidate("U:0:2", "unilateral", 2, bits=4.0, served=3),
        candidate("U:0:1", "unilateral", 1, bits=5.0, served=3),
        candidate("U:1:3", "unilateral", 3, bits=2.0, served=3),
        candidate("J:1:2->3:4", "joint", 4, bits=6.0, served=3),
    )
    monkeypatch.setattr(policy.c3s_policy, "build_s0_catalog", lambda **_kwargs: catalog)
    result = policy.heuristic_lite_catalog(
        SimpleNamespace(eta_ref=Fraction(1)), object(),
    )
    assert [row["profile_id"] for row in result] == [
        "BASE", "U:0:1", "U:1:3", "J:1:2->3:4",
    ]


def test_arm_parser_and_assertion_binding() -> None:
    assert runner.parse_arms(["BASE,HEUR,NULL,LITE"]) == ("LITE", "NULL", "HEUR")
    with pytest.raises(runner.DiagnosticRunnerError, match="requires NULL"):
        runner.panel_bindings(
            horizon=30, arms=("HEUR",), assert_null_equals_base=True,
        )


def churn_observation(users: int = 5) -> SimpleNamespace:
    masks = np.ones((users, runner.donor.f1.NUM_ACTIONS), dtype=np.bool_)
    tables = tuple(SimpleNamespace(
        mask=masks[uid],
        norad_ids=np.arange(runner.donor.f1.NUM_ACTIONS, dtype=np.int64) + 100,
        cell_ids=np.arange(runner.donor.f1.NUM_ACTIONS, dtype=np.int64) + uid,
    ) for uid in range(users))
    return SimpleNamespace(masks=masks, candidates=SimpleNamespace(slot_tables=tables))


def test_random_renew_changes_exactly_one_user_per_decision() -> None:
    users = 5
    observation = churn_observation(users)
    environment = SimpleNamespace(
        _segments=[None] * users, _pending_segment_age=None,
        _previous_association=[None] * users, _step_index=0,
    )
    selector = policy.ChurnSelector(
        arm="RANDOM_RENEW", world=7, lineage=8,
        base_proposer=lambda *_args: np.zeros(users, dtype=np.int64),
    )
    for step in range(3):
        actions = selector.select_actions(environment, observation, np.random.default_rng(99))
        assert np.count_nonzero(actions != 0) == 1
        assert selector.decision_records[-1]["users_changed_vs_base"] == 1
        environment._step_index = step + 1


def test_random_renew_keeps_same_link_as_an_explicit_renewal_option() -> None:
    from mcrl.env.action_contract import Association

    observation = churn_observation(1)
    observation.masks[:] = False
    observation.masks[0, 0] = True
    observation.candidates.slot_tables[0].mask[:] = observation.masks[0]
    environment = SimpleNamespace(
        _segments=[SimpleNamespace(age_steps=2)], _pending_segment_age=None,
        _previous_association=[Association(norad_id=100, cell_id=0)], _step_index=2,
    )
    selector = policy.ChurnSelector(
        arm="RANDOM_RENEW", world=7, lineage=8,
        base_proposer=lambda *_args: np.zeros(1, dtype=np.int64),
    )
    actions = selector.select_actions(environment, observation, np.random.default_rng(1))
    assert actions.tolist() == [0]
    assert selector.decision_records[-1]["edited_users"] == [0]
    assert selector.decision_records[-1]["explicit_renewal_users"] == [0]
    assert selector.decision_records[-1]["users_changed_vs_base"] == 0


def test_base_forced_renew_4_only_renews_users_at_or_above_four() -> None:
    users = 5
    observation = churn_observation(users)
    ages = [1, 4, 3, 8, 0]
    environment = SimpleNamespace(
        _segments=[SimpleNamespace(age_steps=age) for age in ages],
        _pending_segment_age=None, _previous_association=[None] * users,
        _step_index=3,
    )
    selector = policy.ChurnSelector(
        arm="BASE_FORCED_RENEW_4", world=7, lineage=8,
        base_proposer=lambda *_args: np.zeros(users, dtype=np.int64),
    )
    actions = selector.select_actions(environment, observation, np.random.default_rng(1))
    assert np.array_equal(actions, np.zeros(users, dtype=np.int64))
    assert selector.decision_records[-1]["explicit_renewal_users"] == [1, 3]
    assert all(ages[uid] >= 4 for uid in selector.decision_records[-1]["explicit_renewal_users"])


def test_instrumentation_counts_on_synthetic_three_step_world(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mcrl.runtime.ee_axis_state as state_module

    monkeypatch.setattr(
        state_module, "encode_ee_axis_state",
        lambda *_args: SimpleNamespace(state_sha256="b" * 64),
    )
    records: list[dict[str, object]] = []

    def selector(*_args):
        records.append({
            "users_changed_vs_base": len(records),
            "explicit_renewal_users": [],
            "executed_configuration_type": "SYNTHETIC",
        })
        return np.zeros(runner.USERS, dtype=np.int64)

    trajectory = runner.run_arm_trajectory(
        environment=ThreeStepWorld(), env_rng=np.random.default_rng(11),
        mobility_rng=np.random.default_rng(12), horizon=3, selector=selector,
        decision_records=records,
    )
    steps = trajectory["steps"]
    assert [row["association_changed_users"] for row in steps] == [0, 0, 0]
    assert [row["active_beam_count"] for row in steps] == [7, 8, 9]
    assert [row["association_segment_age"]["mean_hex"] for row in steps] == [
        float(1).hex(), float(2).hex(), float(3).hex(),
    ]
    assert [row["users_changed_vs_base"] for row in steps] == [0, 1, 2]
    assert all(row["per_user_transmit_power_sum_w_hex"] == float(82.5).hex() for row in steps)


def test_trajectory_receipts_include_new_instrumentation_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import mcrl.runtime.ee_axis_state as state_module

    monkeypatch.setattr(
        state_module, "encode_ee_axis_state",
        lambda *_args: SimpleNamespace(state_sha256="c" * 64),
    )
    trajectory = runner.run_arm_trajectory(
        environment=ThreeStepWorld(), env_rng=np.random.default_rng(21),
        mobility_rng=np.random.default_rng(22), horizon=3,
        selector=lambda *_args: np.zeros(runner.USERS, dtype=np.int64),
    )
    required = {
        "association_changed_users", "handover_count", "explicit_renewal_count",
        "handover_or_renewal_count", "users_changed_vs_base", "active_beam_count",
        "association_segment_age", "association_segment_age_before_decision",
        "per_user_transmit_power_sum_w_hex",
        "nominal", "realised", "executed_configuration_type",
    }
    assert all(required <= set(step) for step in trajectory["steps"])


def test_ablate_anchor_refreshes_recurrence_to_p0() -> None:
    import datetime as dt
    from mcrl.env.constants import TLE_ROOT_DEFAULT
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.reference_policy import STAY_IF_POSSIBLE, build_reference_policy
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.tle import TleArchive

    archive_path = Path(TLE_ROOT_DEFAULT).expanduser()
    if not archive_path.is_dir():
        pytest.skip("TLE archive not present")
    driver = ScenarioDriver(
        TleArchive(archive_path),
        ScenarioConfig(mobility=MobilityConfig(num_users=5), steps_per_episode=3),
    )
    environment = physics_override.DiagnosticStepEnvironment.construct(
        driver, physics_override=physics_override.get_physics_override("ablate_anchor"),
    )
    rng = np.random.default_rng(31)
    observation = environment.reset(
        dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc), rng,
    )
    policy_impl = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    policy_impl.reset()
    for _step in range(3):
        actions = policy_impl.act(observation.candidates, rng)
        outcome = environment.step(actions, rng)
        served = outcome.resolution.served
        assert np.allclose(
            outcome.link_power_w[served], environment.physics.segment_start_power_w,
        )
        observation = outcome.observation


def test_merge_tables_and_handover_sensitivity_use_instrumented_steps() -> None:
    def step(index: int, bits: float, energy: float, handovers: int) -> dict[str, object]:
        return {
            "step_index": index, "bits_hex": bits.hex(), "energy_j_hex": energy.hex(),
            "served": 3, "opportunities": 3, "dwell_phase_index": index % 4,
            "handover_or_renewal_count": handovers,
            "association_changed_users": handovers, "handover_count": handovers,
            "explicit_renewal_count": 0, "users_changed_vs_base": 0,
            "active_beam_count": 1,
            "association_segment_age": {"mean_hex": float(1).hex(), "histogram": {"1": 3}},
            "association_segment_age_before_decision": {"mean_hex": float(0).hex(), "histogram": {"0": 3}},
            "per_user_transmit_power_sum_w_hex": float(1).hex(),
            "nominal": {"bits_hex": bits.hex(), "energy_j_hex": energy.hex()},
            "realised": {"bits_hex": bits.hex(), "energy_j_hex": energy.hex()},
            "executed_configuration_type": "SYNTHETIC",
        }

    receipt = {
        "selected_diagnostic_arms": ["LITE"],
        "arms": {
            "BASE": {"steps": [step(0, 10.0, 10.0, 0), step(1, 10.0, 10.0, 0)]},
            "LITE": {"steps": [step(0, 11.0, 10.0, 1), step(1, 11.0, 10.0, 2)]},
        },
        "decisions_by_arm": {
            "BASE": [{"wall_seconds_hex": float(0).hex()}] * 2,
            "LITE": [{"wall_seconds_hex": float(0).hex()}] * 2,
        },
    }
    pooled = runner.pool_unit_receipts(
        [receipt], selected_arms=("LITE",), handover_energy_sensitivity=True,
    )
    assert len(pooled["ee_advantage_vs_base_by_segment_age_phase"]["tables"]["LITE"]) == 2
    assert {row["stratum"] for row in pooled["ee_advantage_vs_base_by_handover_count"]["tables"]["LITE"]} == {1, 2}
    sensitivity = pooled["handover_energy_sensitivity"]
    assert len(sensitivity["grid_j_per_handover"]) == 6
    assert sensitivity["handover_count_field"] == "handover_or_renewal_count"


def test_estimate_covers_cheap_new_arms_and_override_binding() -> None:
    result = runner.estimate(
        units=12,
        selected_arms=("RANDOM_RENEW", "RANDOM_RENEW_K", "BASE_FORCED_RENEW_4"),
        physics_override="ablate_anchor",
    )
    assert result["physics_override"]["name"] == "ablate_anchor"
    assert all(
        result["arms"][arm]["relative_to_v1_full_catalog"] == 0.0
        for arm in ("RANDOM_RENEW", "RANDOM_RENEW_K", "BASE_FORCED_RENEW_4")
    )
