"""Focused synthetic checks for the pure V0.23 source-binding seam."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_source_binding_plan.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "v023_source_binding_plan_test",
        MODULE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


plan = _load_module()


def _common(
    *,
    worlds: tuple[str | int, ...] = ("train-world-a", "train-world-b"),
    split: str = "TRAIN",
):
    seeds = (101, 202)
    return plan.CommonBinding(
        split=split,
        world_ids=worlds,
        training_seeds=seeds,
        world_sha256=plan.canonical_sha256({"world_ids": list(worlds)}),
        seed_sha256=plan.canonical_sha256({"training_seeds": list(seeds)}),
    )


COMMON = _common()


def _source(
    route: str,
    mode: str,
    digest_letter: str,
    *,
    rows: int = 12,
    updates: int | None = None,
    initializations: tuple[str | int, ...] | None = None,
    learner_config_sha256: str | None = None,
    common=COMMON,
    identity: str | None = None,
    metadata=None,
):
    rules = {
        ("C1", plan.INFORMED): "c1-informed-source-v1",
        ("C1", plan.CLUSTER_MATCHED_NEUTRAL): plan.C1_CLUSTER_NEUTRAL_SOURCE_RULE,
        ("C2", plan.INFORMED): "c2-informed-source-v1",
        ("C2", plan.EQUAL_BUDGET_NEUTRAL): plan.C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE,
        ("C3", plan.INFORMED): "c3-informed-source-v1",
        ("C3", plan.MATCHED_PLACEBO_NEUTRAL): plan.C3_MATCHED_PLACEBO_SOURCE_RULE,
    }
    normalized = plan._normalize_mode(route, mode)
    route_updates = {"C1": 10, "C2": 3000, "C3": 2000}
    route_initializations = {
        "C1": ("q1-init-a", "q1-init-b", "q1-init-c"),
        "C2": ("q2-init-a", "q2-init-b", "q2-init-c"),
        "C3": ("q3-init-a", "q3-init-b", "q3-init-c"),
    }
    route_configs = {"C1": "a" * 64, "C2": "b" * 64, "C3": "c" * 64}
    selected_initializations = initializations or route_initializations[route]
    return plan.RouteSourceBinding(
        route=route,
        mode=normalized,
        source_sha256=digest_letter * 64,
        row_budget=rows,
        learner_initialization_ids=selected_initializations,
        learner_initialization_sha256=plan.canonical_sha256(
            {"learner_initialization_ids": list(selected_initializations)}
        ),
        learner_config_sha256=learner_config_sha256 or route_configs[route],
        learner_update_count=route_updates[route] if updates is None else updates,
        common=common,
        source_rule=rules[(route, normalized)],
        source_identity=identity,
        metadata={} if metadata is None else metadata,
    )


def _baseline(**kwargs):
    values = {
        "policy_id": "frozen-pre-catfish-main-v1",
        "policy_sha256": "f" * 64,
        "authentication_sha256": "e" * 64,
    }
    values.update(kwargs)
    return plan.BaselinePolicyBinding(**values)


def _make_plan(**overrides):
    values = {
        "common": COMMON,
        "c1_informed": _source("C1", plan.INFORMED, "1", identity="c1-informed"),
        "c1_cluster_neutral": _source(
            "C1", plan.CLUSTER_MATCHED_NEUTRAL, "2", identity="c1-cluster-neutral"
        ),
        "c2_informed": _source("C2", plan.INFORMED, "3", identity="c2-informed"),
        "c2_equal_budget_neutral": _source(
            "C2", plan.EQUAL_BUDGET_NEUTRAL, "4", identity="c2-equal-neutral"
        ),
        "c3_informed": _source("C3", plan.INFORMED, "5", identity="c3-informed"),
        "c3_matched_placebo_neutral": _source(
            "C3", plan.MATCHED_PLACEBO_NEUTRAL, "6", identity="c3-placebo-neutral"
        ),
        "baseline": _baseline(),
    }
    values.update(overrides)
    return plan.build_five_arm_source_binding_plan(**values)


def test_plan_binds_the_five_required_source_semantics_and_exact_hashes():
    binding_plan = _make_plan()

    assert binding_plan.arms == plan.PRIMARY_ARMS
    assert binding_plan.route_learner_update_counts == {
        "C1": 10,
        "C2": 3000,
        "C3": 2000,
    }
    assert binding_plan.route_learner_initialization_ids["C1"] == (
        "q1-init-a",
        "q1-init-b",
        "q1-init-c",
    )
    assert binding_plan.route_source_hashes("FULL") == {
        "C1": "1" * 64,
        "C2": "3" * 64,
        "C3": "5" * 64,
    }
    assert binding_plan.route_source_hashes("DROP_C1") == {
        "C1": "2" * 64,
        "C2": "3" * 64,
        "C3": "5" * 64,
    }
    assert binding_plan.route_source_hashes("DROP_C2")["C2"] == "4" * 64
    assert binding_plan.route_source_hashes("DROP_C3")["C3"] == "6" * 64
    assert binding_plan.for_arm("BASELINE").routes == ()
    assert binding_plan.for_arm("BASELINE").baseline.policy_sha256 == "f" * 64
    assert "common" not in binding_plan.for_arm("BASELINE").baseline.to_dict()
    assert binding_plan.verify() == binding_plan.plan_sha256


def test_plan_digest_is_deterministic_and_tracks_route_hash_changes():
    first = _make_plan()
    second = _make_plan()
    assert first.plan_sha256 == second.plan_sha256

    changed = _make_plan(
        c3_matched_placebo_neutral=_source(
            "C3", plan.MATCHED_PLACEBO_NEUTRAL, "7", identity="c3-placebo-neutral"
        )
    )
    assert changed.plan_sha256 != first.plan_sha256


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("rows", 11, "row budgets must be equal"),
        ("updates", 2999, "update budgets must be equal"),
    ),
)
def test_plan_rejects_unequal_neutral_route_budgets(field, value, message):
    neutral = _source(
        "C2",
        plan.EQUAL_BUDGET_NEUTRAL,
        "4",
        identity="c2-equal-neutral",
        **{field: value},
    )
    with pytest.raises(plan.SourceBindingPlanError, match=message):
        _make_plan(c2_equal_budget_neutral=neutral)


def test_plan_rejects_within_route_initialization_config_world_or_seed_drift():
    drift_common = _common(worlds=("train-world-a", "train-world-c"))
    drifted = _source(
        "C1",
        plan.INFORMED,
        "1",
        common=drift_common,
        identity="c1-informed",
    )
    with pytest.raises(plan.SourceBindingPlanError, match="drift"):
        _make_plan(c1_informed=drifted)

    drifted_neutral_init = _source(
        "C1",
        plan.CLUSTER_MATCHED_NEUTRAL,
        "2",
        initializations=("different-a", "different-b", "different-c"),
        identity="c1-cluster-neutral",
    )
    with pytest.raises(plan.SourceBindingPlanError, match="initialization IDs"):
        _make_plan(c1_cluster_neutral=drifted_neutral_init)

    drifted_neutral_config = _source(
        "C2",
        plan.EQUAL_BUDGET_NEUTRAL,
        "4",
        learner_config_sha256="d" * 64,
        identity="c2-equal-neutral",
    )
    with pytest.raises(plan.SourceBindingPlanError, match="learner configs"):
        _make_plan(c2_equal_budget_neutral=drifted_neutral_config)


def test_plan_allows_route_specific_learner_contracts():
    binding_plan = _make_plan()
    full = binding_plan.for_arm("FULL")
    assert full.route("C1").learner_update_count == 10
    assert full.route("C2").learner_update_count == 3000
    assert full.route("C3").learner_update_count == 2000
    assert len(
        {
            full.route(route).learner_config_sha256
            for route in ("C1", "C2", "C3")
        }
    ) == 3


def test_plan_rejects_test_worlds_and_episode_fields():
    test_common = _common(worlds=("train-world-a", "TEST-world"))
    with pytest.raises(plan.SourceBindingPlanError, match="TEST"):
        _make_plan(common=test_common)

    episode_source = _source(
        "C3",
        plan.MATCHED_PLACEBO_NEUTRAL,
        "6",
        identity="c3-placebo-neutral",
        metadata={"episode_count": 200},
    )
    with pytest.raises(plan.SourceBindingPlanError, match="forbidden episode_count"):
        _make_plan(c3_matched_placebo_neutral=episode_source)


def test_head_drop_is_not_a_primary_efficacy_ablation():
    with pytest.raises(plan.SourceBindingPlanError, match="HEAD_DROP"):
        _make_plan(ablation_mode=plan.HEAD_DROP)

    with pytest.raises(plan.SourceBindingPlanError, match="HEAD_DROP"):
        _make_plan(
            c1_cluster_neutral=_source(
                "C1", plan.HEAD_DROP, "2", identity="c1-head-drop"
            )
        )


def test_plan_rejects_source_aliasing_between_route_replacements():
    aliased = _source(
        "C1",
        plan.CLUSTER_MATCHED_NEUTRAL,
        "1",
        identity="c1-cluster-neutral",
    )
    with pytest.raises(plan.SourceBindingPlanError, match="aliases"):
        _make_plan(c1_cluster_neutral=aliased)

    cross_route = _source(
        "C2",
        plan.INFORMED,
        "1",
        identity="c2-informed",
    )
    with pytest.raises(plan.SourceBindingPlanError, match="aliases"):
        _make_plan(c2_informed=cross_route)


def test_baseline_requires_explicit_authenticated_policy_and_never_q1_plus_q2():
    with pytest.raises(plan.SourceBindingPlanError, match="explicit"):
        _make_plan(baseline=None)

    with pytest.raises(plan.SourceBindingPlanError, match="authenticated"):
        _make_plan(baseline=_baseline(authenticated=False))

    with pytest.raises(plan.SourceBindingPlanError, match=r"Q1\+Q2"):
        plan.bind_authenticated_baseline_policy(
            {
                "policy_id": "assembled",
                "policy_sha256": "f" * 64,
                "authentication_sha256": "e" * 64,
                "authenticated": True,
                "q1": "route-source",
                "q2": "route-source",
            },
        )


def test_baseline_does_not_claim_current_source_learner_contract():
    baseline = _baseline()

    assert not hasattr(baseline, "common")
    assert "common" not in baseline.to_dict()


def test_adapter_binds_only_already_authenticated_source_results():
    class SyntheticSource:
        selection_digest = "8" * 64
        budget = 12
        update_budget = 3000
        learner_initialization_ids = ("q2-init-a", "q2-init-b", "q2-init-c")
        learner_config_sha256 = "b" * 64
        source_rule = plan.C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE
        authenticated = True
        calls = 0

        def verify(self):
            self.calls += 1
            return self.selection_digest

    source = SyntheticSource()
    binding = plan.bind_authenticated_route_source(
        source,
        route="C2",
        mode=plan.EQUAL_BUDGET_NEUTRAL,
        common=COMMON,
        source_identity="synthetic-c2-neutral",
    )
    assert source.calls == 1
    assert binding.source_sha256 == "8" * 64
    assert binding.row_budget == 12
    assert binding.learner_update_count == 3000

    with pytest.raises(plan.SourceBindingPlanError, match="source_sha256 is missing"):
        plan.bind_authenticated_route_source(
            object(),
            route="C1",
            mode=plan.INFORMED,
            common=COMMON,
            row_budget=12,
            source_rule="c1-informed-source-v1",
        )


def test_missing_common_hash_is_rejected_before_plan_construction():
    with pytest.raises(plan.SourceBindingPlanError, match="seed_sha256"):
        replace(COMMON, seed_sha256="missing").verify()
