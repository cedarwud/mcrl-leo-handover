from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

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
import v023_two_route_source_training_runner as source_runner


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


def _write_producer_source_receipt(root: Path) -> Path:
    """Write the Stage-A receipt through its canonical producer method."""

    (root / "checkpoints").mkdir(parents=True)
    for epoch in (0, 100):
        checkpoint = source_runner._checkpoint_path(root, epoch)
        checkpoint.write_bytes(f"producer-checkpoint:{epoch}".encode("ascii"))
        source_runner._write_sidecar(
            checkpoint, source_runner._file_sha256(checkpoint)
        )
    authority = source_runner.RunAuthorityDigests(
        authority_sha256="a" * 64,
        code_sha256="b" * 64,
        input_sha256="c" * 64,
    )
    config = SimpleNamespace(
        orchestrator_config=SimpleNamespace(formal_use=True),
        authority_digests=authority,
        to_payload=lambda: {
            "fixture": "canonical-producer-writer",
            "authority_digests": asdict(authority),
        },
    )
    producer = object.__new__(source_runner.V023TwoRouteSourceTrainingRunner)
    producer.output_root = root
    producer.config = config
    producer.provider_identity = "producer-fixture"
    producer.orchestrator = SimpleNamespace(initialization_sha256="d" * 64)
    producer._write_final_receipt(
        {
            "decision": "PASS_SOURCE_TRAINING_INTEGRITY",
            "checkpoint_sha256": "e" * 64,
        }
    )
    return root / "canonical-receipt.json"


@pytest.fixture
def producer_written_source_receipt(tmp_path: Path) -> Path:
    return _write_producer_source_receipt(tmp_path / "source-run")


def test_runtime_admission_reads_pass_from_canonical_source_writer(
    tmp_path: Path, producer_written_source_receipt: Path
) -> None:
    admission_dir = tmp_path / "admission"
    admission_dir.mkdir()
    for name, payload in (
        ("prereg.json", {"frozen": True}),
        ("tle.json", {"frozen_files": [{"file": "x"}], "file_set_sha256": "a" * 64}),
        ("configuration.json", {"threads": 1}),
    ):
        runner._write_once(admission_dir / name, payload)
    receipt_path = admission_dir / "stage-a.json"
    receipt_path.write_bytes(producer_written_source_receipt.read_bytes())
    payload = {
        "schema": f"{runner.SCHEMA}-runtime-admission-v1",
        "status": "FORMAL_RUNTIME_ADMITTED",
        "split": runner.SPLIT,
        "admitted_evaluation_sha256": "b" * 64,
        "physical_configuration": {
            "users": runner.USERS,
            "steps": runner.STEPS,
            "split": runner.SPLIT,
            "field_component": runner.FIELD_COMPONENT,
            "tle_root": "/home/sat/mcrl-runtime/tle-frozen-20260820",
        },
        "prereg": {"path": "prereg.json", "sha256": runner.file_sha256(admission_dir / "prereg.json")},
        "tle_manifest": {
            "path": "tle.json",
            "sha256": runner.file_sha256(admission_dir / "tle.json"),
            "file_set_sha256": "a" * 64,
        },
        "execution_configuration": {
            "path": "configuration.json",
            "sha256": runner.file_sha256(admission_dir / "configuration.json"),
        },
        "predecessor_pass_receipts": [{
            "path": "stage-a.json",
            "sha256": runner.file_sha256(receipt_path),
            "status": "PASS_SOURCE_TRAINING_INTEGRITY",
        }],
        "sampler": {"part": "train", "as_dict_sha256": "c" * 64},
    }
    admission = admission_dir / "runtime-admission.json"
    runner._write_once(admission, payload)
    digest = runner.file_sha256(admission)
    admission.with_name(admission.name + ".sha256").write_text(
        f"{digest}  {admission.name}\n", encoding="ascii"
    )
    authenticated = runner.authenticate_runtime_admission(
        admission,
        expected_sha256=digest,
        expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY",),
    )
    assert authenticated["authenticated_predecessor_statuses"] == [
        "PASS_SOURCE_TRAINING_INTEGRITY"
    ]


def _sealed_runtime_admission(tmp_path: Path, checkpoint_sha: str) -> dict[str, object]:
    for name, payload in (
        ("prereg.json", {"frozen": True}),
        ("tle.json", {"frozen_files": [{"file": "x"}], "file_set_sha256": "a" * 64}),
        ("configuration.json", {"threads": 1}),
    ):
        runner._write_once(tmp_path / name, payload)
    source_receipt = _write_producer_source_receipt(tmp_path / "source-writer")
    (tmp_path / "stage-a.json").write_bytes(source_receipt.read_bytes())
    provenance = {
        arm: {
            "checkpoint_sha256": checkpoint_sha,
            "source_mapping": {
                "FULL2": ["informed", "informed"],
                "DROP_C1": ["neutral", "informed"],
                "DROP_C2": ["informed", "neutral"],
            }[arm],
            "stage_a_status": "PASS_SOURCE_TRAINING_INTEGRITY",
            "manifest_sha256": runner.canonical_sha256({"arm": arm}),
        }
        for arm in runner.LEARNED_ARMS
    }
    payload = {
        "schema": f"{runner.SCHEMA}-runtime-admission-v1",
        "status": "FORMAL_RUNTIME_ADMITTED",
        "split": runner.SPLIT,
        "admitted_evaluation_sha256": "b" * 64,
        "tle_root": "/home/sat/mcrl-runtime/tle-frozen-20260820",
        "physical_configuration": {
            "users": runner.USERS,
            "steps": runner.STEPS,
            "split": runner.SPLIT,
            "field_component": runner.FIELD_COMPONENT,
            "tle_root": "/home/sat/mcrl-runtime/tle-frozen-20260820",
        },
        "prereg": {"path": "prereg.json", "sha256": runner.file_sha256(tmp_path / "prereg.json")},
        "tle_manifest": {
            "path": "tle.json",
            "sha256": runner.file_sha256(tmp_path / "tle.json"),
            "file_set_sha256": "a" * 64,
        },
        "execution_configuration": {
            "path": "configuration.json",
            "sha256": runner.file_sha256(tmp_path / "configuration.json"),
        },
        "predecessor_pass_receipts": [
            {
                "path": "stage-a.json",
                "sha256": runner.file_sha256(tmp_path / "stage-a.json"),
                "status": "PASS_SOURCE_TRAINING_INTEGRITY",
            }
        ],
        "sampler": {"part": "train", "as_dict_sha256": "c" * 64},
        "learned_training_provenance": provenance,
    }
    path = tmp_path / "runtime-admission.json"
    runner._write_once(path, payload)
    digest = runner.file_sha256(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return runner.authenticate_runtime_admission(
        path,
        expected_sha256=digest,
        expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY",),
    )


class _Policy:
    def __init__(self, arm: str, checkpoint_sha256: str) -> None:
        self.arm = arm
        self.checkpoint_sha256 = checkpoint_sha256
        self.routes = () if arm == "BASELINE" else runner.ROUTES

    def verify(self) -> None:
        return None

    def binding(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "checkpoint_sha256": self.checkpoint_sha256,
            "routes": list(self.routes),
            "fixed_policy": True,
        }


def test_training_provenance_allows_legitimate_identical_policy_bytes(tmp_path: Path) -> None:
    common_sha = "d" * 64
    admission = _sealed_runtime_admission(tmp_path, common_sha)
    policies = tuple(_Policy(arm, common_sha) for arm in runner.ARMS)
    adapter = runner.FixedPolicyEpisodeAdapter(
        policies=policies,
        archive=object(),
        environment_factory=lambda _archive, _users: object(),
        rng_factory=lambda _seed: (),
        runtime_admission=admission,
        required_predecessor_statuses=("PASS_SOURCE_TRAINING_INTEGRITY",),
    )
    assert tuple(adapter.policy_bindings) == runner.ARMS
    assert all(
        "training_provenance" in adapter.policy_bindings[arm]
        for arm in runner.LEARNED_ARMS
    )


def test_runtime_admission_rejects_tampered_predecessor_pass(tmp_path: Path) -> None:
    admission = _sealed_runtime_admission(tmp_path, "d" * 64)
    Path(admission["admission_path"]).parent.joinpath("stage-a.json").write_text(
        '{"status":"STOP_SOURCE_TRAINING_INTEGRITY"}', encoding="ascii"
    )
    with pytest.raises(runner.C1C2PhysicalError, match="bytes disagree"):
        runner.authenticate_runtime_admission(
            admission["admission_path"],
            expected_sha256=admission["admission_sha256"],
            expected_statuses=("PASS_SOURCE_TRAINING_INTEGRITY",),
        )
