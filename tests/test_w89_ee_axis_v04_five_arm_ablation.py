"""W-89 -- synthetic contracts for the frozen V0.4 five-arm evaluator.

No test in this file opens TLE data, constructs a simulator, loads a
checkpoint, trains a network, or runs an episode.  Physical endpoints are
exercised only with sealed-shape synthetic rows.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_five_arm_ablation.py"


def _module():
    spec = importlib.util.spec_from_file_location("v04_five_arm_w89", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(
    runner,
    *,
    policy: str,
    seed: int,
    init: int | None,
    bits: float,
    energy: float = 10.0,
    served: int = 900,
):
    field = runner.common_field_receipt(seed)
    world = hashlib.sha256(f"world:{seed}".encode("ascii")).hexdigest()
    mask = hashlib.sha256(f"mask:{seed}".encode("ascii")).hexdigest()
    return {
        "schema": runner.EPISODE_SCHEMA,
        "policy_label": policy,
        "evaluation_split": "TRAIN",
        "initialization_seed": init,
        "evaluation_seed": seed,
        "selected_q3_rung": 100 if policy != "MAIN" else None,
        "total_q3_update_count": 100 if policy != "MAIN" else None,
        "steps": 10,
        "users": 100,
        "decision_count": 1000,
        "start_epoch": "2026-09-01T00:00:00+00:00",
        "initial_world_sha256": world,
        "initial_state_sha256": world,
        "initial_mask_sha256": mask,
        "fading_field_sha256": field["root_digest"],
        "fading_field_components": field["components"],
        "total_bits": float(bits),
        "total_energy_j": float(energy),
        "ratio_of_sums_ee_bits_per_j": float(bits / energy),
        "served_user_steps": served,
        "served_fraction": served / 1000.0,
        "outage_fraction": 1.0 - served / 1000.0,
        "action_trace_sha256": hashlib.sha256(
            f"{policy}:{seed}:{init}".encode("ascii")
        ).hexdigest(),
        "test_split_opened": False,
        "held_out_ee_evaluated": True,
        "episode_training": False,
    }


def _all_rows(runner):
    rows = {arm: [] for arm in runner.ARMS}
    for seed in runner.EVALUATION_SEEDS:
        for index, init in enumerate(runner.INITIALIZATION_SEEDS):
            rows["FULL"].append(
                _row(runner, policy="FULL", seed=seed, init=init, bits=120.0 + index)
            )
            for arm in runner.ROUTE_ARMS[1:]:
                rows[arm].append(
                    _row(
                        runner,
                        policy=arm,
                        seed=seed,
                        init=init,
                        bits=100.0 + index,
                    )
                )
        rows["MAIN"].append(
            _row(runner, policy="MAIN", seed=seed, init=None, bits=90.0)
        )
    return rows


def test_protocol_is_frozen_to_the_five_arm_train_only_block():
    runner = _module()
    assert runner.EVALUATION_SEEDS == tuple(range(2026092601, 2026092631))
    assert runner.INITIALIZATION_SEEDS == (2026092101, 2026092102, 2026092103)
    assert runner.ARMS == ("FULL", "DROP_C1", "DROP_C2", "DROP_C3", "MAIN")
    assert runner.ROUTE_ARMS == ("FULL", "DROP_C1", "DROP_C2", "DROP_C3")
    assert runner.SELECTED_Q3_RUNG == 100
    assert runner.BOOTSTRAP_REPLICATES == 10_000
    assert runner.BOOTSTRAP_SEEDS == {
        "C1": 2026092691,
        "C2": 2026092692,
        "C3": 2026092693,
        "MAIN": 2026092694,
    }
    assert runner.TEST_SPLIT_OPENED is False
    assert runner.EPISODE_TRAINING is False
    assert runner.EXPECTED_WORK_ORDER_SHA256 == (
        "d58224c63e8a09e82b44e455af9c34454596660d15ddd1e91bad1ec4bb5a3eac"
    )


def test_route_adapter_calls_one_surface_and_one_common_mask_argmax():
    runner = _module()

    class FakeTrainer:
        def __init__(self):
            self.calls = 0

        def q_values_by_route(self, _v03, _v04, _mask):
            self.calls += 1
            return (
                np.asarray([[1.0, 0.0]]),
                np.asarray([[1.0, 0.0]]),
                np.asarray([[0.0, 3.0]]),
            )

    trainer = FakeTrainer()
    state = np.zeros((1, 4), dtype=np.float32)
    mask = np.asarray([[True, True]], dtype=np.bool_)
    assert runner.route_actions(trainer, state, state, mask, "FULL").tolist() == [1]
    assert trainer.calls == 1
    assert runner.route_actions(trainer, state, state, mask, "DROP_C3").tolist() == [0]
    assert trainer.calls == 2
    assert runner.route_actions(trainer, state, state, mask, "DROP_C1").tolist() == [1]
    assert trainer.calls == 3
    assert runner.route_actions(trainer, state, state, mask, "DROP_C2").tolist() == [1]
    assert trainer.calls == 4

    with pytest.raises(runner.V04FiveArmError, match="Boolean"):
        runner.route_actions(trainer, state, state, np.asarray([[1, 1]]), "FULL")


def test_common_field_excludes_arm_and_initialization():
    runner = _module()
    first = runner.common_field_receipt(runner.EVALUATION_SEEDS[0])
    same_world = runner.common_field_receipt(runner.EVALUATION_SEEDS[0])
    other_world = runner.common_field_receipt(runner.EVALUATION_SEEDS[1])
    assert first == same_world
    assert first["root_digest"] != other_world["root_digest"]
    assert first["excluded_components"] == ["initialization_seed", "policy_label"]
    assert first["components"] == [
        runner.FIELD_COMPONENT,
        runner.EXPECTED_C3_CONFIRM_RESULT_SHA256,
        runner.EVALUATION_SEEDS[0],
    ]


def test_result_recomputes_all_five_arms_and_world_cluster_bootstraps():
    runner = _module()
    rows = _all_rows(runner)
    prepare = {
        "evaluator_code_manifest_file_sha256": "a" * 64,
        "evaluator_code_manifest_sha256": "b" * 64,
    }
    authority = {
        "work_order_file_sha256": runner.EXPECTED_WORK_ORDER_SHA256,
        "gate_authority_sha256": "c" * 64,
    }
    result = runner._result_payload(
        prepare=prepare,
        authority=authority,
        rows_by_arm=rows,
        elapsed_s=0.0,
    )
    assert result["episode_count"] == 390
    assert result["full"]["summary"]["rows"] == 90
    assert result["main"]["summary"]["rows"] == 30
    assert result["decision"]["status"] == runner.STATUS_CONFIRM
    for route in runner.ROUTE_NAMES:
        comparison = result["comparisons"][route]
        assert comparison["bootstrap"]["replicates"] == 10_000
        assert comparison["bootstrap"]["world_count"] == 30
        assert comparison["decision"]["status"] == f"CONFIRM_{route}"
    assert result["comparisons"]["MAIN"]["decision"]["status"] == "FULL_BEATS_MAIN"

    with pytest.raises(runner.V04FiveArmError, match="exactly five arms"):
        runner._result_payload(
            prepare=prepare,
            authority=authority,
            rows_by_arm={"FULL": rows["FULL"]},
            elapsed_s=0.0,
        )


def test_bootstrap_and_aggregate_fail_closed_on_nonpositive_energy():
    runner = _module()
    rows = _all_rows(runner)
    broken = copy.deepcopy(rows["DROP_C1"])
    broken[0]["total_energy_j"] = 0.0
    broken[0]["ratio_of_sums_ee_bits_per_j"] = broken[0]["total_bits"] / 0.000001
    with pytest.raises(runner.V04FiveArmError, match="positive"):
        runner.aggregate_rows(broken)


def test_hybrid_snapshot_detects_training_flag_mutation():
    runner = _module()
    networks = torch.nn.ModuleList(
        [torch.nn.Linear(3, 2), torch.nn.Linear(3, 2), torch.nn.Linear(3, 2)]
    )

    class FakeTrainer:
        q_nets = networks
        q3_optimizer = torch.optim.Adam(networks[2].parameters(), lr=0.001)
        q3_update_count = 100

    networks.eval()
    before = runner._snapshot_hybrid(FakeTrainer())
    runner._assert_hybrid_unchanged(FakeTrainer(), before)
    networks[0].train()
    with pytest.raises(runner.V04FiveArmError, match="training_flags"):
        runner._assert_hybrid_unchanged(FakeTrainer(), before)


def test_main_world_service_diagnostic_uses_three_initialization_weight():
    runner = _module()
    rows = _all_rows(runner)
    per_world = runner._per_world_main(rows["FULL"], rows["MAIN"])
    assert per_world[0]["main_served_user_steps_raw"] == 900
    assert per_world[0]["main_served_user_steps_weighted"] == 2700
    assert per_world[0]["served_fraction_difference"] == 0.0

