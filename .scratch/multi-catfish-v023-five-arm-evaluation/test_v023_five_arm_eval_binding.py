from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "v023_five_arm_eval_binding.py"
SPEC = importlib.util.spec_from_file_location("v023_five_arm_eval_binding", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def _common_payload() -> dict[str, object]:
    worlds = ["source-world-a", "source-world-b"]
    seeds = [101, 202]
    return {
        "split": "TRAIN_DEVELOPMENT",
        "world_ids": worlds,
        "training_seeds": seeds,
        "world_sha256": module.canonical_sha256({"world_ids": worlds}),
        "seed_sha256": module.canonical_sha256({"training_seeds": seeds}),
    }


def _route(
    route: str, mode: str, digit: str, *, common: dict[str, object]
) -> dict[str, object]:
    initializations = {
        "C1": ["q1-a", "q1-b", "q1-c"],
        "C2": ["q2-a", "q2-b", "q2-c"],
        "C3": ["q3-a", "q3-b", "q3-c"],
    }[route]
    updates = {"C1": 10, "C2": 3000, "C3": 2000}[route]
    config = {"C1": "a" * 64, "C2": "b" * 64, "C3": "c" * 64}[route]
    return {
        "route": route,
        "mode": mode,
        "source_sha256": digit * 64,
        "source_rule": f"{route.lower()}-{mode.lower()}",
        "row_budget": 12,
        "learner_initialization_ids": initializations,
        "learner_initialization_count": len(initializations),
        "learner_initialization_sha256": module.canonical_sha256(
            {"learner_initialization_ids": initializations}
        ),
        "learner_config_sha256": config,
        "learner_update_count": updates,
        "source_identity": f"{route}-{mode}-{digit}",
        "common": common,
    }


def _source_plan() -> dict[str, object]:
    common = _common_payload()
    c1_i = _route("C1", "INFORMED", "1", common=common)
    c1_n = _route("C1", "CLUSTER_MATCHED_NEUTRAL", "2", common=common)
    c2_i = _route("C2", "INFORMED", "3", common=common)
    c2_n = _route("C2", "EQUAL_BUDGET_NEUTRAL", "4", common=common)
    c3_i = _route("C3", "INFORMED", "5", common=common)
    c3_n = _route("C3", "MATCHED_PLACEBO_NEUTRAL", "6", common=common)
    arms: list[dict[str, object]] = [
        {
            "arm": "FULL",
            "routes": [c1_i, c2_i, c3_i],
            "baseline": None,
            "ablation_mode": module.SOURCE_ABLATION,
        },
        {
            "arm": "BASELINE",
            "routes": [],
            "baseline": {
                "policy_id": "pre-catfish-modqn-main",
                "policy_sha256": "a" * 64,
                "authentication_sha256": "b" * 64,
                "source_kind": module.BASELINE_SOURCE_KIND,
                "source_identity": "training-2026-08-25-rerun01",
            },
            "ablation_mode": None,
        },
        {
            "arm": "DROP_C1",
            "routes": [c1_n, c2_i, c3_i],
            "baseline": None,
            "ablation_mode": module.SOURCE_ABLATION,
        },
        {
            "arm": "DROP_C2",
            "routes": [c1_i, c2_n, c3_i],
            "baseline": None,
            "ablation_mode": module.SOURCE_ABLATION,
        },
        {
            "arm": "DROP_C3",
            "routes": [c1_i, c2_i, c3_n],
            "baseline": None,
            "ablation_mode": module.SOURCE_ABLATION,
        },
    ]
    payload: dict[str, object] = {
        "schema": module.SOURCE_PLAN_SCHEMA,
        "schema_version": 2,
        "ablation_mode": module.SOURCE_ABLATION,
        "common": common,
        "arms": arms,
    }
    payload["plan_sha256"] = module.canonical_sha256(payload)
    return payload


def _policies(plan: dict[str, object]) -> tuple[object, ...]:
    values = []
    for index, arm in enumerate(module.ARMS):
        block = next(row for row in plan["arms"] if row["arm"] == arm)
        values.append(
            module.FrozenPolicyBinding(
                arm=arm,
                policy_id=f"policy-{arm.lower()}",
                policy_family=(
                    "AUTHENTICATED_PRE_CATFISH_MODQN"
                    if arm == "BASELINE"
                    else "MULTI_CATFISH_MCRL_V023"
                ),
                checkpoint_sha256=("a" * 64 if arm == "BASELINE" else f"{index + 1:x}" * 64),
                authentication_sha256=f"{index + 8:x}" * 64,
                source_plan_sha256=plan["plan_sha256"],
                source_arm_sha256=module.canonical_sha256(block),
            )
        )
    return tuple(values)


def _worlds(count: int = 100) -> tuple[object, ...]:
    return tuple(
        module.EvaluationWorldBinding(
            episode_index=index,
            world_id=f"world-{index:06d}",
            world_seed=2026091000 + index,
            field_root_digest=f"{(index % 15) + 1:x}" * 64,
        )
        for index in range(1, count + 1)
    )


def _binding() -> object:
    plan = _source_plan()
    return module.bind_five_arm_evaluation(
        source_plan=plan,
        policies=_policies(plan),
        worlds=_worlds(),
        evaluation_contract_sha256="f" * 64,
    )


def test_valid_binding_is_content_addressed_and_five_arm() -> None:
    binding = _binding()
    payload = binding.to_dict()
    assert [policy["arm"] for policy in payload["policies"]] == list(module.ARMS)
    assert payload["episode_budget"] == 100
    assert payload["checkpoint_every"] == 100
    assert payload["head_drop"] is False
    assert len(payload["binding_sha256"]) == 64


def test_baseline_must_match_explicit_pre_catfish_checkpoint() -> None:
    plan = _source_plan()
    policies = list(_policies(plan))
    baseline = policies[1]
    policies[1] = module.FrozenPolicyBinding(
        **{**baseline.to_dict(), "checkpoint_sha256": "c" * 64}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="pre-Catfish"):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=policies,
            worlds=_worlds(),
            evaluation_contract_sha256="f" * 64,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("head_drop", True, "head drop"),
        ("episode_training", True, "episode training"),
        ("test_split_opened", True, "crossed TEST"),
        ("checkpoint_selected_from_outcome", True, "outcomes"),
        ("fixed_policy", False, "not frozen"),
    ],
)
def test_forbidden_policy_shortcuts_fail_closed(
    field: str, value: bool, message: str
) -> None:
    plan = _source_plan()
    policies = list(_policies(plan))
    policy = policies[0]
    policies[0] = module.FrozenPolicyBinding(
        **{**policy.to_dict(), field: value}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match=message):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=policies,
            worlds=_worlds(),
            evaluation_contract_sha256="f" * 64,
        )


def test_drop_arm_must_retain_all_three_routes() -> None:
    plan = _source_plan()
    drop = next(row for row in plan["arms"] if row["arm"] == "DROP_C3")
    drop["routes"] = drop["routes"][:2]
    plan["plan_sha256"] = module.canonical_sha256(
        {key: value for key, value in plan.items() if key != "plan_sha256"}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="retain C1, C2, and C3"):
        module.verify_source_plan_payload(plan)


def test_drop_arm_cannot_claim_informed_source_for_dropped_route() -> None:
    plan = _source_plan()
    drop = next(row for row in plan["arms"] if row["arm"] == "DROP_C2")
    drop["routes"][1]["mode"] = "INFORMED"
    plan["plan_sha256"] = module.canonical_sha256(
        {key: value for key, value in plan.items() if key != "plan_sha256"}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="route modes"):
        module.verify_source_plan_payload(plan)


def test_source_digest_must_be_well_formed() -> None:
    plan = _source_plan()
    full = next(row for row in plan["arms"] if row["arm"] == "FULL")
    full["routes"][0]["source_sha256"] = "not-a-digest"
    plan["plan_sha256"] = module.canonical_sha256(
        {key: value for key, value in plan.items() if key != "plan_sha256"}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="lowercase SHA-256"):
        module.verify_source_plan_payload(plan)


def test_source_plan_digest_drift_is_rejected() -> None:
    plan = _source_plan()
    plan["common"] = {"split": "TRAIN_DEVELOPMENT", "drift": True}
    with pytest.raises(module.FiveArmEvaluationBindingError, match="digest drifted"):
        module.verify_source_plan_payload(plan)


def test_policy_checkpoint_alias_between_arms_is_rejected() -> None:
    plan = _source_plan()
    policies = list(_policies(plan))
    right = policies[-1]
    policies[-1] = module.FrozenPolicyBinding(
        **{**right.to_dict(), "checkpoint_sha256": policies[0].checkpoint_sha256}
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="alias"):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=policies,
            worlds=_worlds(),
            evaluation_contract_sha256="f" * 64,
        )


def test_world_budget_must_land_on_100_episode_checkpoint() -> None:
    plan = _source_plan()
    with pytest.raises(module.FiveArmEvaluationBindingError, match="100-episode"):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=_policies(plan),
            worlds=_worlds(99),
            evaluation_contract_sha256="f" * 64,
        )


def test_world_ids_cannot_cross_test() -> None:
    plan = _source_plan()
    worlds = list(_worlds())
    worlds[0] = module.EvaluationWorldBinding(
        episode_index=1,
        world_id="TEST-world-1",
        world_seed=worlds[0].world_seed,
        field_root_digest=worlds[0].field_root_digest,
    )
    with pytest.raises(module.FiveArmEvaluationBindingError, match="TEST"):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=_policies(plan),
            worlds=worlds,
            evaluation_contract_sha256="f" * 64,
        )


def test_arm_order_is_fixed() -> None:
    plan = _source_plan()
    policies = list(_policies(plan))
    policies[0], policies[1] = policies[1], policies[0]
    with pytest.raises(module.FiveArmEvaluationBindingError, match="order or coverage"):
        module.bind_five_arm_evaluation(
            source_plan=plan,
            policies=policies,
            worlds=_worlds(),
            evaluation_contract_sha256="f" * 64,
        )


def test_consumer_accepts_real_heterogeneous_source_plan_v2() -> None:
    source_module_path = (
        HERE.parent
        / "multi-catfish-v023-ablation-prep"
        / "v023_source_binding_plan.py"
    )
    spec = importlib.util.spec_from_file_location(
        "v023_source_binding_plan_integration", source_module_path
    )
    assert spec is not None and spec.loader is not None
    source = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = source
    spec.loader.exec_module(source)

    worlds = ("source-world-a", "source-world-b")
    seeds = (101, 202)
    common = source.CommonBinding(
        split="TRAIN_DEVELOPMENT",
        world_ids=worlds,
        training_seeds=seeds,
        world_sha256=source.canonical_sha256({"world_ids": list(worlds)}),
        seed_sha256=source.canonical_sha256({"training_seeds": list(seeds)}),
    )

    def route_binding(route, mode, digit, rule, updates, config):
        initializations = tuple(f"{route.lower()}-init-{index}" for index in range(3))
        return source.RouteSourceBinding(
            route=route,
            mode=mode,
            source_sha256=digit * 64,
            row_budget=12,
            learner_initialization_ids=initializations,
            learner_initialization_sha256=source.canonical_sha256(
                {"learner_initialization_ids": list(initializations)}
            ),
            learner_config_sha256=config * 64,
            learner_update_count=updates,
            common=common,
            source_rule=rule,
            source_identity=f"{route}-{mode}",
        )

    built = source.build_five_arm_source_binding_plan(
        common=common,
        c1_informed=route_binding("C1", source.INFORMED, "1", "c1-informed-v1", 10, "a"),
        c1_cluster_neutral=route_binding(
            "C1",
            source.CLUSTER_MATCHED_NEUTRAL,
            "2",
            source.C1_CLUSTER_NEUTRAL_SOURCE_RULE,
            10,
            "a",
        ),
        c2_informed=route_binding("C2", source.INFORMED, "3", "c2-informed-v1", 3000, "b"),
        c2_equal_budget_neutral=route_binding(
            "C2",
            source.EQUAL_BUDGET_NEUTRAL,
            "4",
            source.C2_EQUAL_BUDGET_NEUTRAL_SOURCE_RULE,
            3000,
            "b",
        ),
        c3_informed=route_binding("C3", source.INFORMED, "5", "c3-informed-v1", 2000, "c"),
        c3_matched_placebo_neutral=route_binding(
            "C3",
            source.MATCHED_PLACEBO_NEUTRAL,
            "6",
            source.C3_MATCHED_PLACEBO_SOURCE_RULE,
            2000,
            "c",
        ),
        baseline=source.BaselinePolicyBinding(
            policy_id="pre-catfish-main",
            policy_sha256="d" * 64,
            authentication_sha256="e" * 64,
        ),
    )
    assert built.route_learner_update_counts == {
        "C1": 10,
        "C2": 3000,
        "C3": 2000,
    }
    assert module.verify_source_plan_payload(built.to_dict()) == built.plan_sha256
