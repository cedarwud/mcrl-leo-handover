"""Focused positive, continuation, parity, and mutation tests."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import ee_axis_two_route_model as MODEL
import v023_two_route_learner_orchestrator as ORCH
import v023_two_route_source_training_runner as RUNNER
from v023_two_route_test_helpers import c1_batch, c2_batch, model_config, stub_provider


@pytest.fixture(scope="module", autouse=True)
def _single_torch_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def _runner_config(*, budget: int = 100) -> RUNNER.FrozenSourceTrainingConfig:
    return RUNNER.FrozenSourceTrainingConfig(
        epoch_budget=budget,
        orchestrator_config=ORCH.V023TwoRouteOrchestratorConfig.formal(
            model_config=model_config(), train_seed=17
        ),
        provider_factory_spec="fixtures:make_provider",
        authority_digests=RUNNER.RunAuthorityDigests("a" * 64, "b" * 64, "c" * 64),
    )


def _assert_tree_identical(left: Any, right: Any) -> None:
    assert type(left) is type(right)
    if isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, Mapping):
        assert tuple(left) == tuple(right)
        for key in left:
            _assert_tree_identical(left[key], right[key])
    elif isinstance(left, (list, tuple)):
        assert len(left) == len(right)
        for first, second in zip(left, right, strict=True):
            _assert_tree_identical(first, second)
    else:
        assert left == right


def test_cycle_order_update_counts_and_closed_source_map():
    provider = stub_provider()
    orchestrator = ORCH.V023TwoRouteLearnerOrchestrator(
        ORCH.V023TwoRouteOrchestratorConfig.formal(
            model_config=model_config(), train_seed=17
        ),
        provider,
    )
    receipts = orchestrator.advance_many(200)
    assert tuple(receipt.route for receipt in receipts[:4]) == ("C1", "C2", "C1", "C2")
    assert orchestrator.completed_source_training_epochs == 100
    assert orchestrator.update_cursor == 200
    assert orchestrator.route_update_counts == {"C1": 100, "C2": 100}
    assert len(provider.calls) == 400
    assert ORCH.ARMS == ("FULL2", "DROP_C1", "DROP_C2")
    assert ORCH.ROUTE_ORDER == ("C1", "C2")
    assert RUNNER.SOURCE_MAP == {
        "FULL2": ("informed", "informed"),
        "DROP_C1": ("neutral", "informed"),
        "DROP_C2": ("informed", "neutral"),
    }
    assert {arm: dict(routes) for arm, routes in ORCH.SOURCE_ABLATION_MAP.items()} == {
        "FULL2": {"C1": "informed", "C2": "informed"},
        "DROP_C1": {"C1": "neutral", "C2": "informed"},
        "DROP_C2": {"C1": "informed", "C2": "neutral"},
    }
    for receipt in receipts[:2]:
        assert [(item.arm, item.source) for item in receipt.arm_updates] == [
            (arm, ORCH.SOURCE_ABLATION_MAP[arm][receipt.route]) for arm in ORCH.ARMS
        ]


def test_model_checkpoint_digests_reject_q3_and_three_route_checkpoint():
    model = MODEL.EEAxisTwoRouteModel(model_config(), train_seed=17)
    assert len(model.q_networks) == len(model.optimizers) == 2
    assert not hasattr(model, "q3")
    state = model.checkpoint_state(
        update_count=0, route_update_counts={"C1": 0, "C2": 0}
    )
    assert state["schema"] == MODEL.TWO_ROUTE_CHECKPOINT_SCHEMA
    assert state["routes"] == ["C1", "C2"]
    assert set(state["initialization"]) == {
        "bytes_sha256", "head_state_sha256", "optimizer_state_sha256"
    }
    assert set(state["heads"]) == set(state["optimizers"]) == {"C1", "C2"}

    q3_mutation = deepcopy(state)
    q3_mutation["heads"]["Q3"] = deepcopy(q3_mutation["heads"]["C2"])
    with pytest.raises(MODEL.EEAxisTwoRouteError, match="Q3"):
        model.load_checkpoint_state(q3_mutation)

    from mcrl.algorithms.ee_axis_lcsrs_three_route import (
        EEAxisLCSRSThreeRoute,
        LCSRSThreeRouteConfig,
    )

    three = EEAxisLCSRSThreeRoute(
        LCSRSThreeRouteConfig(q1=model_config().q1, q2=model_config().q2),
        train_seed=17,
    ).checkpoint_state(update_count=0)
    with pytest.raises(MODEL.EEAxisTwoRouteError, match="Q3|three-route"):
        model.load_checkpoint_state(three)


def test_epoch_zero_export_reload_has_bitwise_exact_continuation(tmp_path: Path):
    provider = stub_provider()
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(_runner_config(), provider)
    root = tmp_path / "source-run"
    runner.begin_new(root)

    manifest = json.loads((root / "exports/epoch-0000.json").read_text(encoding="utf-8"))
    assert [entry["arm"] for entry in manifest["exports"]] == list(RUNNER.ARMS)
    exported = RUNNER._read_torch(root / manifest["exports"][0]["path"])
    resumed_model = MODEL.EEAxisTwoRouteModel(model_config(), train_seed=17)
    assert resumed_model.load_checkpoint_state(exported) == 0
    resumed_trainer = ORCH.V023TwoRouteTrainer(resumed_model)
    resumed_trainer.update_route("C1", c1_batch(2.0))
    resumed_trainer.update_route("C2", c2_batch(2.0))

    runner.run_to_epoch(1)
    expected = runner.orchestrator.models["FULL2"].checkpoint_state(
        update_count=2, route_update_counts={"C1": 1, "C2": 1}
    )
    actual = resumed_model.checkpoint_state(
        update_count=2, route_update_counts={"C1": 1, "C2": 1}
    )
    _assert_tree_identical(expected, actual)

    resumed_runner = RUNNER.V023TwoRouteSourceTrainingRunner(_runner_config(), stub_provider())
    resumed_runner.resume_from_checkpoint(root / "checkpoints/epoch-0000.runner.pt")
    resumed_runner.run_to_epoch(1)
    _assert_tree_identical(
        runner.orchestrator.checkpoint_state(), resumed_runner.orchestrator.checkpoint_state()
    )


def test_runner_writes_fixed_epoch_zero_and_hundred_exports_and_receipt(tmp_path: Path):
    provider = stub_provider()
    runner = RUNNER.V023TwoRouteSourceTrainingRunner(_runner_config(), provider)
    root = tmp_path / "formal-source-run"
    runner.begin_new(root)
    runner.run()
    assert runner.completed_epochs == 100
    assert sorted(path.name for path in (root / "checkpoints").glob("*.runner.pt")) == [
        "epoch-0000.runner.pt", "epoch-0100.runner.pt"
    ]
    assert sorted(path.name for path in (root / "exports").glob("epoch-*.json")) == [
        "epoch-0000.json", "epoch-0100.json"
    ]
    final = json.loads((root / "canonical-receipt.json").read_text(encoding="utf-8"))
    assert final["claim_ceiling"] == RUNNER.CLAIM_CEILING
    assert final["completed_updates"] == 200
    assert [entry["epoch"] for entry in final["checkpoints"]] == [0, 100]
    assert [path.name.split("-", 1)[1].split(".current", 1)[0]
            for path in sorted((root / "exports/epoch-0100").glob("*.pt"))] == list(RUNNER.ARMS)


def test_mutation_negatives_third_route_fourth_arm_and_budget_500(tmp_path: Path):
    with pytest.raises(ORCH.V023TwoRouteOrchestratorError, match="third route"):
        ORCH.V023TwoRouteLearnerOrchestrator(
            ORCH.V023TwoRouteOrchestratorConfig.formal(
                model_config=model_config(), train_seed=17
            ),
            stub_provider(routes=("C1", "C2", "C3")),
        )
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="budget 500"):
        _runner_config(budget=500)

    runner = RUNNER.V023TwoRouteSourceTrainingRunner(_runner_config(), stub_provider())
    root = tmp_path / "mutations"
    runner.begin_new(root)
    checkpoint = deepcopy(RUNNER._read_torch(root / "checkpoints/epoch-0000.runner.pt"))
    checkpoint["arm_order"].append("FOURTH_ARM")
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="fourth arm"):
        runner._validate_checkpoint(checkpoint)

    for forbidden in ("ALL_NEUTRAL_CONTROL", "FULL", "DROP_C3", "BASELINE"):
        changed = deepcopy(RUNNER._read_torch(root / "checkpoints/epoch-0000.runner.pt"))
        changed["arm_order"] = [forbidden, "DROP_C1", "DROP_C2"]
        with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="forbidden"):
            runner._validate_checkpoint(changed)
    with pytest.raises(RUNNER.V023TwoRouteSourceTrainingRunnerError, match="TEST"):
        RUNNER.V023TwoRouteSourceTrainingRunner(
            _runner_config(), stub_provider()
        ).begin_new(tmp_path / "TEST" / "rejected")


def test_deploy_function_matches_existing_physical_carrier_on_random_inputs():
    physical_directory = HERE.parent / "multi-catfish-v023-physical"
    sys.path.insert(0, str(physical_directory))
    try:
        physical = importlib.import_module("v023_physical_episode_runner")
    finally:
        sys.path.remove(str(physical_directory))
    rng = np.random.default_rng(20260907)
    for _ in range(25):
        q1 = rng.normal(size=(7, 28)).astype(np.float32)
        q2 = rng.normal(size=(7, 28)).astype(np.float32)
        masks = rng.random((7, 28)) > 0.3
        masks[:, 0] = True
        expected = physical._masked_argmax(
            np.asarray(q1, dtype=np.float64) + np.asarray(q2, dtype=np.float64), masks
        )
        actual = MODEL.deploy_q12_action(q1, q2, masks)
        assert np.array_equal(actual, expected)
    q1 = np.zeros((1, 28), dtype=np.float32)
    q2 = np.zeros((1, 28), dtype=np.float32)
    masks = np.zeros((1, 28), dtype=np.bool_)
    masks[0, (3, 9)] = True
    assert MODEL.deploy_q12_action(q1, q2, masks).tolist() == [3]
