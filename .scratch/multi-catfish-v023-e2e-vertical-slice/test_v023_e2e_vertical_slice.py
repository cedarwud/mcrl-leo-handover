"""Seconds-scale full plumbing chain using only a fake TrainerEnvironment."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
from dataclasses import asdict

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v023_vertical_slice_test", HERE / "v023_e2e_vertical_slice.py")
assert SPEC is not None and SPEC.loader is not None
slice_api = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = slice_api
SPEC.loader.exec_module(slice_api)


class FakeEnvironment:
    def __init__(self) -> None:
        self.config = SimpleNamespace(num_users=100, steps_per_episode=10)
        self.environment = SimpleNamespace(_fading_field=None, driver=SimpleNamespace(config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=0.25))))
        self.index = 0

    def reset(self, *_rngs):
        self.index = 0
        return None, None, "o-0"

    def step(self, _actions, _rng):
        self.index += 1
        self.last_outcome = SimpleNamespace(
            link_rate_bps=np.full(100, 4.0), system_power_w=8.0,
            resolution=SimpleNamespace(served_count=70), observation=f"o-{self.index}",
            done=self.index == 10,
        )

    def training_state_dict(self):
        return {"step": self.index}


def _native(_environment, observation):
    value = float(observation.split("-")[-1])
    return SimpleNamespace(state_matrix=np.full((100, 3), value, dtype=np.float32), action_masks=np.ones((100, 28), dtype=bool))


def _binding_and_world():
    markers = {"FULL": ("c", "1"), "BASELINE": ("a", "b"), "DROP_C1": ("d", "2"), "DROP_C2": ("e", "3"), "DROP_C3": ("f", "4")}
    policies = tuple(SimpleNamespace(arm=arm, checkpoint_sha256=markers[arm][0] * 64, source_arm_sha256=markers[arm][1] * 64, policy_family="INITIAL_NETWORK") for arm in slice_api.ARMS)
    binding = SimpleNamespace(policies=policies, verify=lambda: "9" * 64)
    seed = 2026121999
    root = slice_api.adapter_api._physical.KeyedFadingField.from_components(slice_api.adapter_api._physical.FIELD_COMPONENT, seed).root_digest
    world = SimpleNamespace(episode_index=1, world_id="vertical-plumbing-world-000001", world_seed=seed, field_root_digest=root)
    return binding, world


def test_source_plan_to_fixture_policy_to_five_physical_receipts_chain():
    binding, world = _binding_and_world()
    fixtures = slice_api.build_initial_network_plumbing_policies(binding)
    admission = SimpleNamespace(request=SimpleNamespace(binding=binding))
    adapter = slice_api.adapter_api.RealFiveArmExecutionAdapter(
        admission=admission, policies=fixtures, tle_archive=object(),
        environment_factory=lambda *_: FakeEnvironment(),
        rng_factory=lambda seed: (np.random.default_rng(seed), np.random.default_rng(seed + 1)),
        encode_native_state=_native, c3_view_factory=lambda *_: object(),
        trainer_environment_type=FakeEnvironment,
    )
    receipt = slice_api.run_one_world_plumbing_slice(adapter=adapter, world=world, policies=fixtures)
    assert receipt["status"] == "PLUMBING_ONLY_NOT_GATE_NOT_EFFICACY"
    assert receipt["receipt_count"] == 5 and receipt["arms"] == list(slice_api.ARMS)
    assert receipt["zero_learner_updates"] is True and receipt["evaluable_policy_artifacts"] is False
    rows = receipt["receipts"]
    assert all(row["total_bits"] == pytest.approx(1000.0) and row["total_energy_j"] == pytest.approx(20.0) for row in rows)
    assert {row["field_root_digest"] for row in rows} == {world.field_root_digest}
    assert all(row["head_drop"] is False and row["test_split_opened"] is False for row in rows)
    assert "GO" not in repr(receipt) and "admission" not in repr(receipt).lower()


def test_rejects_test_and_real_launch_without_five_policy_loader():
    binding, world = _binding_and_world()
    fixtures = slice_api.build_initial_network_plumbing_policies(binding)
    with pytest.raises(slice_api.V023VerticalSliceError, match="TRAIN-only"):
        slice_api.run_one_world_plumbing_slice(adapter=object(), world=world, policies=fixtures, split="TEST")
    with pytest.raises(slice_api.V023VerticalSliceError, match="five-policy loader"):
        slice_api.real_launch_blocker()
    with pytest.raises(slice_api.V023VerticalSliceError, match="not a current evaluable"):
        slice_api.require_real_five_policy_loader(fixtures)


def test_current_three_route_class_is_present_and_old_q3_or_modqn_is_rejected():
    from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
    from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
    from mcrl.algorithms.ee_axis_lcsrs_three_route import EEAxisLCSRSThreeRoute, LCSRSThreeRouteConfig
    from mcrl.algorithms.modqn import MODQNTrainer

    q12 = EEAxisActionSharedConfig(
        state_dim=228, action_dim=28, hidden_layers=(8,), activation="relu",
        learning_rate=0.001, kappa_bits=1.0, beta=0.0, loss_weights=(1.0, 1.0, 1.0),
    )
    model = EEAxisLCSRSThreeRoute(LCSRSThreeRouteConfig(q12=q12), train_seed=7)
    assert isinstance(model.q3, LCSRSC3QNetwork) and len(model.q_networks) == 3
    bridge = slice_api.adapter_api._runner.V023LCSRSThreeRoutePolicy(model)
    assert bridge.model is model
    with pytest.raises(slice_api.adapter_api._runner.V023LCSRSPolicyError, match="current"):
        slice_api.adapter_api._runner.V023LCSRSThreeRoutePolicy(LCSRSC3QNetwork())
    with pytest.raises(slice_api.adapter_api._runner.V023LCSRSPolicyError, match="current"):
        slice_api.adapter_api._runner.V023LCSRSThreeRoutePolicy(object.__new__(MODQNTrainer))


def test_loader_rejects_head_drop_and_the_authenticated_split_d40_payload():
    binding, _world = _binding_and_world()
    dropped = list(binding.policies)
    dropped[-1] = SimpleNamespace(**vars(dropped[-1]), head_drop=True)
    with pytest.raises(slice_api.V023VerticalSliceError, match="head-drop"):
        slice_api.build_initial_network_plumbing_policies(SimpleNamespace(policies=tuple(dropped)))

    checkpoint = slice_api.REPO / (
        ".scratch/multi-catfish-v020-c3-source-audit/repriced-q1-q2-fit/"
        "lineage-2026092101/checkpoints/lineage-2026092101-q2init-2026108101-rung-003000.pt"
    )
    if not checkpoint.is_file():
        pytest.skip("authenticated d40 fixture is not present in this checkout")
    artifact = slice_api.adapter_api._runner.ArtifactBinding(
        role="q12", path=checkpoint,
        sha256=slice_api.adapter_api._runner.CURRENT_Q12_CHECKPOINT_SHA256,
    )
    with pytest.raises(slice_api.V023VerticalSliceError, match="V0.20 split q1/q2"):
        slice_api.build_current_initial_network_policy_fixtures(
            source_binding=binding, q12_artifact=artifact,
        )


def test_current_loaded_fixture_factory_uses_three_route_models_and_separate_ids(tmp_path, monkeypatch):
    import torch
    from mcrl.algorithms.ee_axis_action_shared import (
        ACTION_SHARED_ALGORITHM, ACTION_SHARED_CHECKPOINT_VERSION,
        EEAxisActionSharedConfig,
    )
    from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
    from mcrl.algorithms.ee_axis_lcsrs_three_route import EEAxisLCSRSThreeRoute, LCSRSThreeRouteConfig

    q12 = EEAxisActionSharedConfig(
        state_dim=228, action_dim=28, hidden_layers=(8,), activation="relu",
        learning_rate=0.001, kappa_bits=1.0, beta=0.0, loss_weights=(1.0, 1.0, 1.0),
    )
    source = EEAxisLCSRSThreeRoute(LCSRSThreeRouteConfig(q12=q12), train_seed=71)
    artifact_path = tmp_path / "action-shared-d40-test.pt"
    torch.save({
        "algorithm": ACTION_SHARED_ALGORITHM,
        "format_version": ACTION_SHARED_CHECKPOINT_VERSION,
        "config": asdict(q12),
        "q_networks": [network.state_dict() for network in source.q_networks],
    }, artifact_path)
    digest = slice_api.adapter_api._runner.file_sha256(artifact_path)
    monkeypatch.setattr(slice_api.adapter_api._runner, "CURRENT_Q12_CHECKPOINT_SHA256", digest)
    artifact = slice_api.adapter_api._runner.ArtifactBinding(role="q12", path=artifact_path, sha256=digest)
    binding, _world = _binding_and_world()

    fixtures = slice_api.build_current_initial_network_policy_fixtures(
        source_binding=binding, q12_artifact=artifact, seed_base=2026135300,
    )

    assert tuple(fixtures) == slice_api.ARMS
    assert all(isinstance(policy.model.q3, LCSRSC3QNetwork) for policy in fixtures.values())
    assert all(policy.evaluable_policy_artifact is False for policy in fixtures.values())
    assert len({policy.checkpoint_sha256 for policy in fixtures.values()}) == len(slice_api.ARMS)
    assert all(policy.policy_family.startswith("INITIAL_NETWORK::") for policy in fixtures.values())
