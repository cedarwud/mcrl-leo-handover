from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import run_v023_c3s_variants as runner
import variant_policy as policy


def metric(bits: float, energy: float = 1.0, served: int = 2) -> dict[str, object]:
    return {"total_bits": bits, "total_energy_j": energy, "served": served, "opportunities": 2}


def row(profile: str, kind: str, actions: list[int], bits: float) -> dict[str, object]:
    tie = (0,) if profile == "BASE" else ((1, 0, actions[0]) if kind == "unilateral" else (2, 1, 1, 2, 2))
    return {"profile_id": profile, "kind": kind, "actions": np.asarray(actions, dtype=np.int64),
            "tie_key": tie, "nominal": metric(bits)}


def fake_adapter(arm: str) -> SimpleNamespace:
    constants = policy.load_constants()
    adapter = SimpleNamespace(
        arm=arm, eta_ref=Fraction(1), constants=constants, hooks=policy.hooks_for(arm),
        margin_fraction=Fraction(1, 1000), kappa_bits=Fraction("10097071012.757404"),
        cadence_steps=3, cadence_residue=0, hysteresis_steps=3,
        blocked_through={}, decision_index=0,
    )
    return adapter


def test_all_levers_are_declared_once_in_config() -> None:
    constants = policy.load_constants()
    assert tuple(constants["arms"]) == runner.ARMS
    assert constants["V-C.cadence_steps"] == 3
    assert constants["V-H.exclusion_steps"] == 3
    assert Fraction(constants["V-P.persistence_kappa_bits"]) == Fraction("10097071012.757404")


def test_evacuation_only_and_unilateral_only_catalogs() -> None:
    catalog = (row("BASE", "base", [0, 0], 10), row("U:0:1", "unilateral", [1, 0], 11),
               row("J:1:1->2:2", "joint", [1, 1], 12))
    vj = policy.hooks_for("V-J").catalog_builder(catalog, None, fake_adapter("V-J"))
    vu = policy.hooks_for("V-U").catalog_builder(catalog, None, fake_adapter("V-U"))
    assert [item["kind"] for item in vj] == ["base", "joint"]
    assert [item["kind"] for item in vu] == ["base", "unilateral"]


def test_unilateral_lite_enumeration_is_base_plus_one_physical_alternative_per_user(monkeypatch: pytest.MonkeyPatch) -> None:
    tables = []
    for user in range(2):
        tables.append(SimpleNamespace(
            mask=np.asarray([True, True, True] + [False] * 25, dtype=np.bool_),
            norad_ids=np.asarray([10 + user, 20 + user, 30 + user] + [-1] * 25, dtype=np.int64),
            cell_ids=np.asarray([1, 2, 3] + [-1] * 25, dtype=np.int64),
        ))
    full = []
    for user in range(2):
        for action in (1, 2):
            actions = np.zeros(2, dtype=np.int64); actions[user] = action
            full.append({"focal_user": user, "candidate_action": action, "candidate_joint_actions": actions})
    monkeypatch.setattr(policy.v1.f1, "enumerate_unilateral_candidates", lambda _observation, _reference: tuple(full))
    q12 = np.zeros((2, 28), dtype=np.float32)
    q12[:, 0] = 3; q12[:, 2] = 2; q12[:, 1] = 1
    result = policy.v1._lite_unilateral_skeletons(
        SimpleNamespace(candidates=SimpleNamespace(slot_tables=tuple(tables))),
        np.zeros(2, dtype=np.int64), q12,
    )
    assert [(item["focal_user"], item["candidate_action"]) for item in result] == [(0, 2), (1, 2)]


def test_margin_gate_requires_configured_fraction_of_base_nominal_bits() -> None:
    adapter = fake_adapter("V-M")
    base = row("BASE", "base", [0, 0], 1000)
    below = row("U:0:1", "unilateral", [1, 0], 1000.999)
    edge = row("U:0:1", "unilateral", [1, 0], 1001)
    context = policy.DecisionContext(step_index=0)
    assert not adapter.hooks.gate(below, base, context, adapter)
    assert adapter.hooks.gate(edge, base, context, adapter)


def test_cadence_coordinates_only_at_zero_mod_three() -> None:
    adapter = fake_adapter("V-C")
    base, selected = row("BASE", "base", [0, 0], 1), row("U:0:1", "unilateral", [1, 0], 2)
    assert [adapter.hooks.gate(selected, base, policy.DecisionContext(step_index=t), adapter) for t in range(7)] == [True, False, False, True, False, False, True]


def test_hysteresis_excludes_coordinator_moved_user_for_next_three_steps_but_not_base() -> None:
    adapter = fake_adapter("V-H")
    base = row("BASE", "base", [0, 0], 1)
    moved = row("U:0:1", "unilateral", [1, 0], 2)
    adapter.hooks.post_decision_state(moved, base, policy.DecisionContext(step_index=4), adapter)
    for decision in (5, 6, 7):
        adapter.decision_index = decision
        result = adapter.hooks.catalog_builder((base, moved), SimpleNamespace(base_actions=base["actions"]), adapter)
        assert result == (base,)
    adapter.decision_index = 8
    assert adapter.hooks.catalog_builder((base, moved), SimpleNamespace(base_actions=base["actions"]), adapter) == (base, moved)


def test_persistence_term_exact_arithmetic_with_mocked_chi() -> None:
    kappa = Fraction("10097071012.757404")
    result = policy.persistence_objective(metric(20, 2), eta_ref=Fraction(3), persistence=[1, 0, 1, 0], kappa_bits=kappa)
    assert result == Fraction(14) - 2 * kappa
    with pytest.raises(policy.VariantPolicyError, match="binary"):
        policy.persistence_objective(metric(1), eta_ref=Fraction(1), persistence=[0.5], kappa_bits=kappa)


def test_lookahead_objective_sums_both_intervals() -> None:
    assert policy.lookahead_objective(metric(12, 2), metric(9, 3), eta_ref=Fraction(2)) == 11


def test_selection_service_guard_and_margin_gate() -> None:
    adapter = fake_adapter("V-M")
    base = row("BASE", "base", [0, 0], 1000)
    low_service = row("U:0:1", "unilateral", [1, 0], 2000); low_service["nominal"]["served"] = 1
    tiny = row("U:1:1", "unilateral", [0, 1], 1000.5)
    selected, _, _ = policy.select_with_hooks((base, low_service, tiny), context=policy.DecisionContext(step_index=0), adapter=adapter)
    assert selected["profile_id"] == "BASE"


def test_nine_arms_and_coordinator_state_are_independent() -> None:
    environments = {arm: SimpleNamespace(history=[]) for arm in runner.ARMS}
    adapters = {arm: policy.VariantPolicyAdapter(physical=object(), frozen=object(), arm=arm, eta_ref=Fraction(1))
                for arm in runner.COORDINATOR_ARMS}
    environments["BASE"].history.append(1)
    adapters["V-H"].blocked_through[7] = 3
    adapters["LITE"].decision_records.append({"only": "lite"})
    assert len({id(value) for value in environments.values()}) == 9
    assert len({id(value) for value in adapters.values()}) == 8
    assert all(not value.history for arm, value in environments.items() if arm != "BASE")
    assert all(7 not in value.blocked_through for arm, value in adapters.items() if arm != "V-H")
    assert all(not value.decision_records for arm, value in adapters.items() if arm != "LITE")


def test_association_reversal_within_three_steps() -> None:
    a, b, c = (1, 1), (2, 2), (3, 3)
    trace = [(a, c), (b, c), (b, c), (a, c), (b, c)]
    assert policy.association_reversals(trace, window=3) == 2


def test_exact_pooling_kill_rule_curves_latency_and_catalog_reports() -> None:
    arms = {}
    decisions = {}
    for arm in runner.ARMS:
        bits = 1.0 if arm == "BASE" else 2.0
        steps = [
            {"step_index": index, "bits_hex": bits.hex(), "energy_j_hex": (1.0).hex(),
             "served": 2, "opportunities": 2}
            for index in range(runner.HORIZON)
        ]
        arms[arm] = {
            "steps": steps, "decision_wall_seconds_hex": [(0.25).hex()] * runner.HORIZON,
            "association_reversals_within_3_steps": 0, "catalog_sizes": [1] * runner.HORIZON,
        }
        if arm != "BASE":
            decisions[arm] = [{"action_changed": False, "catalog_size": 1}] * runner.HORIZON
    pooled = runner.pool_unit_receipts([{"arms": arms, "decisions_by_arm": decisions}])
    assert runner._from_payload(pooled["arms"]["BASE"]["eta"]) == 1
    assert all(pooled["decisions"][arm]["outcome"] == "SUPPORT" for arm in runner.COORDINATOR_ARMS)
    assert all(len(pooled["cumulative_curves"][arm]) == runner.HORIZON for arm in runner.ARMS)
    assert pooled["latency_by_arm"]["BASE"]["latency_over_threshold_count"] == 0
    assert pooled["catalog_sizes_by_arm"]["LITE"] == {"minimum": 1, "maximum": 1, "mean": 1.0}
    assert pooled["catalog_sizes_by_arm"]["BASE"] == {"minimum": 1, "maximum": 1, "mean": 1.0}


def test_refusals_for_unknown_arm_unsealed_contract_and_nonlocal_write(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    with pytest.raises(policy.VariantPolicyError, match="unknown"):
        policy.hooks_for("FULL")
    monkeypatch.setattr(runner, "CONTRACT_PATH", tmp_path / "absent.md")
    with pytest.raises(runner.VariantRunnerError, match="controller must place"):
        runner.sealed_contract_binding()
    with pytest.raises(runner.VariantRunnerError, match="must remain inside"):
        runner.write_once_with_sidecar(tmp_path / "outside.json", {"x": 1})


def test_write_once_seals_and_refuses_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "HERE", tmp_path)
    target = tmp_path / "receipt.json"
    _, sidecar, digest = runner.write_once_with_sidecar(target, {"value": 1})
    assert target.stat().st_mode & 0o777 == 0o444
    assert sidecar.stat().st_mode & 0o777 == 0o444
    assert sidecar.read_text(encoding="ascii").split() == [digest, target.name]
    with pytest.raises(runner.VariantRunnerError, match="refusing to overwrite"):
        runner.write_once_with_sidecar(target, {"value": 2})
