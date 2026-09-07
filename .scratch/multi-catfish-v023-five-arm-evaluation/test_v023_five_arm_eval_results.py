from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


binding_module = _load("v023_five_arm_eval_binding", "v023_five_arm_eval_binding.py")
results = _load("v023_five_arm_eval_results", "v023_five_arm_eval_results.py")


def _route(
    route: str,
    mode: str,
    digit: str,
    *,
    common: dict[str, object],
) -> dict[str, object]:
    initializations = {
        "C1": ["q1-a", "q1-b", "q1-c"],
        "C2": ["q2-a", "q2-b", "q2-c"],
        "C3": ["q3-a", "q3-b", "q3-c"],
    }[route]
    return {
        "route": route,
        "mode": mode,
        "source_sha256": digit * 64,
        "source_rule": f"{route.lower()}-{mode.lower()}",
        "row_budget": 12,
        "learner_initialization_ids": initializations,
        "learner_initialization_count": len(initializations),
        "learner_initialization_sha256": binding_module.canonical_sha256(
            {"learner_initialization_ids": initializations}
        ),
        "learner_config_sha256": {
            "C1": "a" * 64,
            "C2": "b" * 64,
            "C3": "c" * 64,
        }[route],
        "learner_update_count": {"C1": 10, "C2": 3000, "C3": 2000}[route],
        "source_identity": f"{route}-{mode}-{digit}",
        "common": common,
    }


def _binding(world_count: int = 100):
    source_worlds = ["source-world-a", "source-world-b"]
    source_seeds = [101, 202]
    common = {
        "split": "TRAIN_DEVELOPMENT",
        "world_ids": source_worlds,
        "training_seeds": source_seeds,
        "world_sha256": binding_module.canonical_sha256(
            {"world_ids": source_worlds}
        ),
        "seed_sha256": binding_module.canonical_sha256(
            {"training_seeds": source_seeds}
        ),
    }
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
            "ablation_mode": binding_module.SOURCE_ABLATION,
        },
        {
            "arm": "BASELINE",
            "routes": [],
            "baseline": {
                "policy_id": "main-modqn",
                "policy_sha256": "a" * 64,
                "authentication_sha256": "b" * 64,
                "source_kind": binding_module.BASELINE_SOURCE_KIND,
                "source_identity": "old-main",
            },
            "ablation_mode": None,
        },
        {
            "arm": "DROP_C1",
            "routes": [c1_n, c2_i, c3_i],
            "baseline": None,
            "ablation_mode": binding_module.SOURCE_ABLATION,
        },
        {
            "arm": "DROP_C2",
            "routes": [c1_i, c2_n, c3_i],
            "baseline": None,
            "ablation_mode": binding_module.SOURCE_ABLATION,
        },
        {
            "arm": "DROP_C3",
            "routes": [c1_i, c2_i, c3_n],
            "baseline": None,
            "ablation_mode": binding_module.SOURCE_ABLATION,
        },
    ]
    source_plan: dict[str, object] = {
        "schema": binding_module.SOURCE_PLAN_SCHEMA,
        "schema_version": 2,
        "ablation_mode": binding_module.SOURCE_ABLATION,
        "common": common,
        "arms": arms,
    }
    source_plan["plan_sha256"] = binding_module.canonical_sha256(source_plan)
    policies = []
    for index, arm in enumerate(binding_module.ARMS):
        block = next(row for row in arms if row["arm"] == arm)
        policies.append(
            binding_module.FrozenPolicyBinding(
                arm=arm,
                policy_id=f"policy-{arm}",
                policy_family=("MODQN" if arm == "BASELINE" else "MULTI_CATFISH_V023"),
                checkpoint_sha256=("a" * 64 if arm == "BASELINE" else f"{index + 1:x}" * 64),
                authentication_sha256=f"{index + 8:x}" * 64,
                source_plan_sha256=source_plan["plan_sha256"],
                source_arm_sha256=binding_module.canonical_sha256(block),
            )
        )
    worlds = tuple(
        binding_module.EvaluationWorldBinding(
            episode_index=index,
            world_id=f"world-{index:06d}",
            world_seed=2026092000 + index,
            field_root_digest=f"{index % 15 + 1:x}" * 64,
        )
        for index in range(1, world_count + 1)
    )
    return binding_module.bind_five_arm_evaluation(
        source_plan=source_plan,
        policies=policies,
        worlds=worlds,
        evaluation_contract_sha256="f" * 64,
    )


def _receipts(binding, through: int = 100):
    binding_sha = binding.verify()
    policies = {policy.arm: policy for policy in binding.policies}
    rows = []
    for world in binding.worlds[:through]:
        for arm_index, arm in enumerate(binding_module.ARMS):
            policy = policies[arm]
            energy = 1000.0 + arm_index
            bits = (100_000_000.0 + 1_000_000.0 * (4 - arm_index)) * energy
            served = 999 - arm_index
            rows.append(
                results.FiveArmEpisodeReceipt(
                    schema=results.RECEIPT_SCHEMA,
                    arm=arm,
                    episode_index=world.episode_index,
                    world_id=world.world_id,
                    world_seed=world.world_seed,
                    field_root_digest=world.field_root_digest,
                    initial_world_sha256=f"{world.episode_index % 15 + 1:x}" * 64,
                    policy_checkpoint_sha256=policy.checkpoint_sha256,
                    source_arm_sha256=policy.source_arm_sha256,
                    evaluation_binding_sha256=binding_sha,
                    action_trace_sha256=f"{arm_index + 1:x}" * 64,
                    total_bits=bits,
                    total_energy_j=energy,
                    ratio_of_sums_ee_bits_per_j=bits / energy,
                    served_user_steps=served,
                    service_opportunities=1000,
                    service_fraction=served / 1000,
                )
            )
    return rows


def test_checkpoint_pools_ratio_of_sums_and_keeps_decision_null() -> None:
    binding = _binding()
    payload = results.build_checkpoint_payload(
        binding=binding, receipts=_receipts(binding), through_episode=100
    )
    assert payload["receipt_count"] == 500
    assert payload["scientific_decision"] is None
    assert payload["pooled_by_arm"]["FULL"]["episodes"] == 100
    assert payload["pooled_by_arm"]["FULL"]["ratio_of_sums_ee_bits_per_j"] == pytest.approx(104_000_000.0)
    assert payload["comparisons"]["FULL_VS_BASELINE"]["relative_difference_percent"] > 0
    assert len(payload["checkpoint_sha256"]) == 64


def test_final_result_is_complete_but_unadjudicated() -> None:
    binding = _binding()
    payload = results.build_result_payload(binding=binding, receipts=_receipts(binding))
    assert payload["status"] == "COMPLETE_UNADJUDICATED"
    assert payload["scientific_decision"] is None
    assert len(payload["result_sha256"]) == 64


def test_missing_arm_row_is_rejected() -> None:
    binding = _binding()
    rows = _receipts(binding)
    rows.pop()
    with pytest.raises(results.FiveArmEvaluationResultError, match="receipt count"):
        results.build_checkpoint_payload(
            binding=binding, receipts=rows, through_episode=100
        )


def test_mismatched_initial_world_is_rejected() -> None:
    binding = _binding()
    rows = _receipts(binding)
    row = rows[0]
    rows[0] = results.FiveArmEpisodeReceipt(
        **{**row.to_dict(), "initial_world_sha256": "e" * 64}
    )
    with pytest.raises(results.FiveArmEvaluationResultError, match="initial_world"):
        results.build_checkpoint_payload(
            binding=binding, receipts=rows, through_episode=100
        )


def test_wrong_policy_checkpoint_is_rejected() -> None:
    binding = _binding()
    rows = _receipts(binding)
    row = rows[0]
    rows[0] = results.FiveArmEpisodeReceipt(
        **{**row.to_dict(), "policy_checkpoint_sha256": "e" * 64}
    )
    with pytest.raises(results.FiveArmEvaluationResultError, match="checkpoint provenance"):
        results.build_checkpoint_payload(
            binding=binding, receipts=rows, through_episode=100
        )


def test_head_drop_receipt_is_rejected() -> None:
    binding = _binding()
    rows = _receipts(binding)
    row = rows[0]
    rows[0] = results.FiveArmEpisodeReceipt(**{**row.to_dict(), "head_drop": True})
    with pytest.raises(results.FiveArmEvaluationResultError, match="head_drop"):
        results.build_checkpoint_payload(
            binding=binding, receipts=rows, through_episode=100
        )


def test_episode_ee_must_equal_bits_over_energy() -> None:
    binding = _binding()
    rows = _receipts(binding)
    row = rows[0]
    rows[0] = results.FiveArmEpisodeReceipt(
        **{**row.to_dict(), "ratio_of_sums_ee_bits_per_j": 1.0}
    )
    with pytest.raises(results.FiveArmEvaluationResultError, match="bits/energy"):
        results.build_checkpoint_payload(
            binding=binding, receipts=rows, through_episode=100
        )


def test_checkpoint_cadence_is_not_relaxed() -> None:
    binding = _binding()
    with pytest.raises(results.FiveArmEvaluationResultError, match="100-episode"):
        results.build_checkpoint_payload(
            binding=binding, receipts=_receipts(binding, through=99), through_episode=99
        )
