"""Fake-environment checks for the real five-arm execution seam."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("five_arm_real_adapter", HERE / "v023_real_five_arm_execution_adapter.py")
assert SPEC is not None and SPEC.loader is not None
adapter_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter_module
SPEC.loader.exec_module(adapter_module)

SHA = "a" * 64


class FakePolicy:
    def __init__(self, arm: str, action: int) -> None:
        self.arm = arm
        self.action = action
        marker = {"FULL": "c", "BASELINE": "a", "DROP_C1": "d", "DROP_C2": "e", "DROP_C3": "f"}[arm]
        self.checkpoint_sha256 = marker * 64
        self.source_arm_sha256 = {"FULL": "1", "BASELINE": "b", "DROP_C1": "2", "DROP_C2": "3", "DROP_C3": "4"}[arm] * 64
        self.policy_family = "CURRENT"
        self.head_drop = False
        self.calls: list[str] = []

    def select_actions(self, *, native_state, c3_view, native_observation_event_digest):
        self.calls.append(native_observation_event_digest)
        return np.full(100, self.action, dtype=np.int64)


class FakeTrainerEnvironment:
    def __init__(self) -> None:
        self.config = SimpleNamespace(num_users=100, steps_per_episode=10)
        self.environment = SimpleNamespace(
            _fading_field=None,
            driver=SimpleNamespace(config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=0.5))),
        )
        self.index = 0
        self.loaded = None

    def reset(self, *_rngs):
        self.index = 0
        return None, None, "observation-0"

    def step(self, _actions, _rng):
        self.index += 1
        self.last_outcome = SimpleNamespace(
            link_rate_bps=np.full(100, 2.0), system_power_w=4.0,
            resolution=SimpleNamespace(served_count=50), observation=f"observation-{self.index}",
            done=self.index == 10,
        )

    def training_state_dict(self):
        return {"index": self.index}

    def load_training_state_dict(self, state):
        self.loaded = state


def _native(_step_environment, observation):
    # Observation makes each per-step policy call observably explicit.
    value = float(str(observation).split("-")[-1])
    return SimpleNamespace(state_matrix=np.full((100, 2), value, dtype=np.float32), action_masks=np.ones((100, 28), dtype=bool))


def _admission_and_policies():
    policies = {arm: FakePolicy(arm, index) for index, arm in enumerate(adapter_module.ARMS)}
    frozen = tuple(SimpleNamespace(arm=arm, checkpoint_sha256=policy.checkpoint_sha256, source_arm_sha256=policy.source_arm_sha256, policy_family=policy.policy_family) for arm, policy in policies.items())
    binding = SimpleNamespace(policies=frozen, verify=lambda: "c" * 64)
    return SimpleNamespace(request=SimpleNamespace(binding=binding)), policies


def _world(index: int = 1):
    seed = 2026121800 + index
    root = adapter_module._physical.KeyedFadingField.from_components(adapter_module._physical.FIELD_COMPONENT, seed).root_digest
    return SimpleNamespace(episode_index=index, world_id=f"world-{index:06d}", world_seed=seed, field_root_digest=root)


def _adapter():
    admission, policies = _admission_and_policies()
    adapter = adapter_module.RealFiveArmExecutionAdapter(
        admission=admission, policies=policies, tle_archive=object(),
        environment_factory=lambda _archive, _users: FakeTrainerEnvironment(),
        rng_factory=lambda seed: (np.random.default_rng(seed), np.random.default_rng(seed + 1)),
        encode_native_state=_native, c3_view_factory=lambda *_args: object(),
        trainer_environment_type=FakeTrainerEnvironment,
    )
    return adapter, policies


def test_routes_each_arm_to_its_explicit_policy_and_aggregates_real_outcomes():
    adapter, policies = _adapter()
    world = _world()
    receipts = [adapter.run_episode(arm=arm, world=world, policy=policies[arm], resume_state=None) for arm in adapter_module.ARMS]
    assert [row.arm for row in receipts] == list(adapter_module.ARMS)
    assert all(len(policies[arm].calls) == 10 for arm in adapter_module.ARMS)
    assert all(row.field_root_digest == world.field_root_digest for row in receipts)
    assert all(row.total_bits == pytest.approx(1000.0) and row.total_energy_j == pytest.approx(20.0) for row in receipts)
    assert all(row.ratio_of_sums_ee_bits_per_j == pytest.approx(50.0) and row.service_fraction == pytest.approx(0.5) for row in receipts)
    assert all(row.head_drop is False and row.fixed_policy is True for row in receipts)


def test_resume_state_is_arm_specific_and_restorable():
    adapter, policies = _adapter()
    first = _world(1)
    adapter.run_episode(arm="FULL", world=first, policy=policies["FULL"], resume_state=None)
    state = adapter.resume_state_for("FULL")
    assert state is not None and state["arm"] == "FULL" and state["episode_index"] == 1
    adapter.restore_resume_states({arm: (state if arm == "FULL" else None) for arm in adapter_module.ARMS})
    resumed = adapter.run_episode(arm="FULL", world=_world(2), policy=policies["FULL"], resume_state=adapter.resume_state_for("FULL"))
    assert resumed.episode_index == 2


def test_rejects_missing_gate_or_legacy_synthetic_policy_mode():
    _admission, policies = _admission_and_policies()
    with pytest.raises(adapter_module.RealFiveArmExecutionAdapterError, match="admission"):
        adapter_module.RealFiveArmExecutionAdapter(
            admission=None, policies=policies, tle_archive=object(), environment_factory=lambda *_: FakeTrainerEnvironment(),
            rng_factory=lambda _: (np.random.default_rng(), np.random.default_rng()), encode_native_state=_native,
            c3_view_factory=lambda *_: object(), trainer_environment_type=FakeTrainerEnvironment,
        )
    with pytest.raises(adapter_module.RealFiveArmExecutionAdapterError, match="admission request"):
        adapter_module.build_real_five_arm_execution_adapter(request=None)
    admission, policies = _admission_and_policies()
    policies["DROP_C3"].policy_family = "SYNTHETIC"
    with pytest.raises(adapter_module.RealFiveArmExecutionAdapterError, match="family"):
        adapter_module.RealFiveArmExecutionAdapter(
            admission=admission, policies=policies, tle_archive=object(), environment_factory=lambda *_: FakeTrainerEnvironment(),
            rng_factory=lambda _: (np.random.default_rng(), np.random.default_rng()), encode_native_state=_native,
            c3_view_factory=lambda *_: object(), trainer_environment_type=FakeTrainerEnvironment,
        )
    admission, _ = _admission_and_policies()
    policies["DROP_C3"].checkpoint_sha256 = "not-a-digest"
    with pytest.raises(adapter_module.RealFiveArmExecutionAdapterError, match="checkpoint"):
        adapter_module.RealFiveArmExecutionAdapter(
            admission=admission, policies=policies, tle_archive=object(), environment_factory=lambda *_: FakeTrainerEnvironment(),
            rng_factory=lambda _: (np.random.default_rng(), np.random.default_rng()), encode_native_state=_native,
            c3_view_factory=lambda *_: object(), trainer_environment_type=FakeTrainerEnvironment,
        )
