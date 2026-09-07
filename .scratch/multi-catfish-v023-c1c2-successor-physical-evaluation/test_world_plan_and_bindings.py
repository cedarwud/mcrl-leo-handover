from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest
import torch
import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SOURCE_RUNNER = REPO / ".scratch" / "multi-catfish-v023-two-route-source-training-runner"
for path in (HERE, REPO / "src", SOURCE_RUNNER):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_v023_c1c2_successor_world_plan as builder
import v023_c1c2_successor_physical_runner as runner


def _reseal(payload: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(payload)
    result.pop("plan_sha256", None)
    result["plan_sha256"] = builder.canonical_sha256(result)
    return result


def test_world_plan_is_deterministic_and_digest_bound(tmp_path: Path) -> None:
    first = builder.build_world_plan()
    second = builder.build_world_plan()
    assert first == second
    assert first["plan_sha256"] == builder.verify_world_plan(first)
    assert first["episode_budget"] == 9000
    assert first["worlds"][0] == {
        "episode_index": 1,
        "world_id": "world-000001",
        "world_seed": 2026090601,
        "field_root_digest": builder.keyed_field_root_digest(
            builder.FIELD_COMPONENT, 2026090601
        ),
    }
    assert first["worlds"][-1]["world_id"] == "world-009000"
    assert first["worlds"][-1]["world_seed"] == 2026099600

    target = tmp_path / "world-plan.json"
    builder._write_once(target, first)
    assert builder.read_world_plan(target) == first


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value["arms"].append("DROP_C3"), "declared 9000-world plan"),
        (lambda value: value.__setitem__("split", "TEST"), "declared 9000-world plan"),
        (
            lambda value: value["worlds"][0].__setitem__("world_seed", 7),
            "declared 9000-world plan",
        ),
    ],
)
def test_world_plan_rejects_fifth_arm_test_and_drift(mutation, message: str) -> None:
    payload = builder.build_world_plan()
    mutation(payload)
    payload = _reseal(payload)
    with pytest.raises(builder.WorldPlanError, match=message):
        builder.verify_world_plan(payload)


@pytest.fixture(scope="module")
def producer_checkpoint(tmp_path_factory: pytest.TempPathFactory):
    from ee_axis_two_route_model import (
        EEAxisTwoRouteConfig,
        EEAxisTwoRouteModel,
    )
    from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
    from mcrl.algorithms.ee_axis_v014_head import EEAxisV014HeadConfig

    config_raw = json.loads(
        (
            REPO
            / ".scratch"
            / "multi-catfish-v023-c1c2-successor"
            / "V023-C1C2-SUCCESSOR-MODEL-CONFIG.json"
        ).read_text(encoding="utf-8")
    )
    q1 = dict(config_raw["q1"])
    q2 = dict(config_raw["q2"])
    q1["hidden_layers"] = tuple(q1["hidden_layers"])
    q1["loss_weights"] = tuple(q1["loss_weights"])
    q2["hidden_layers"] = tuple(q2["hidden_layers"])
    model = EEAxisTwoRouteModel(
        EEAxisTwoRouteConfig(
            q1=EEAxisActionSharedConfig(**q1),
            q2=EEAxisV014HeadConfig(**q2),
        ),
        train_seed=2927175120652069826,
    )
    # Producer-owned writer: the fixture is not a hand-shaped mirror of the loader.
    payload = model.checkpoint_state(
        update_count=200,
        route_update_counts={"C1": 100, "C2": 100},
    )
    path = tmp_path_factory.mktemp("producer-checkpoint") / "FULL2.pt"
    torch.save(payload, path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload, path, digest


def test_producer_checkpoint_loads_and_baseline_routes_are_empty(
    producer_checkpoint,
) -> None:
    _payload, path, digest = producer_checkpoint
    policy = runner.load_learned_two_route_checkpoint(
        path, arm="FULL2", expected_sha256=digest
    )
    assert policy.routes == ("C1", "C2")
    assert policy.binding()["routes"] == ["C1", "C2"]
    assert runner.FrozenBaselinePolicy.__dataclass_fields__["routes"].default == ()


def test_loader_rejects_c3_state_from_producer_checkpoint(
    producer_checkpoint, tmp_path: Path
) -> None:
    payload, _path, _digest = producer_checkpoint
    mutated = copy.deepcopy(payload)
    mutated["q3"] = {"state": "forbidden"}
    target = tmp_path / "with-q3.pt"
    torch.save(mutated, target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(runner.C1C2PhysicalError, match="Q3/C3"):
        runner.load_learned_two_route_checkpoint(
            target,
            arm="FULL2",
            expected_sha256=digest,
        )


def test_evaluation_plan_rejects_a_fifth_arm() -> None:
    payload = builder.build_world_plan()
    worlds = tuple(runner.WorldBinding(**row) for row in payload["worlds"])
    plan = runner.EvaluationPlan(
        worlds=worlds,
        plan_sha256=payload["plan_sha256"],
        arms=(*runner.ARMS, "DROP_C3"),
    )
    with pytest.raises(runner.C1C2PhysicalError, match="fixed four-arm order"):
        plan.verify()


def test_learned_deployment_is_unweighted_masked_and_lowest_index_on_ties() -> None:
    q1 = np.zeros((2, 28), dtype=np.float32)
    q2 = np.zeros((2, 28), dtype=np.float32)
    masks = np.zeros((2, 28), dtype=np.bool_)
    masks[0, [3, 7]] = True
    masks[1, [1, 4]] = True
    q1[1, 1] = 1.0
    q2[1, 4] = 2.0
    assert runner.select_learned_q12_actions(q1, q2, masks).tolist() == [3, 4]
