"""Fast current-class checks for the V0.23 real one-world plumbing seam.

Only the expensive TLE construction and native physical encoder are replaced.
The five policies remain actual current ``EEAxisLCSRSThreeRoute`` instances and
their action route still passes through an authenticated structured ``C3View``.
"""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "v023_real_one_world_plumbing_under_test", HERE / "v023_real_one_world_plumbing.py"
)
assert SPEC is not None and SPEC.loader is not None
API = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = API
SPEC.loader.exec_module(API)


def _config():
    from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
    from mcrl.algorithms.ee_axis_lcsrs_three_route import LCSRSThreeRouteConfig

    return LCSRSThreeRouteConfig(
        q12=EEAxisActionSharedConfig(
            state_dim=228,
            action_dim=28,
            hidden_layers=(4,),
            activation="relu",
            learning_rate=1.0e-3,
            kappa_bits=10_097_071_012.757404,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        )
    )


def _c3_view(snapshot, *, action: int):
    """A real immutable C3View with one legal selected action per fake user."""

    from mcrl.runtime.ee_axis_lcsrs_c3_state import assemble_c3_view

    users = snapshot.users
    context = np.zeros((users, 28, 29), dtype=np.float32)
    tokens = np.zeros((users, 28, users + 1, 38), dtype=np.float32)
    action_mask = np.zeros((users, 28), dtype=np.bool_)
    action_mask[:, action] = True
    token_mask = np.zeros((users, 28, users + 1), dtype=np.bool_)
    token_mask[:, :, users] = action_mask
    tokens[:, :, users, 1][action_mask] = 1.0  # exact pair-token type [0, 1]
    return assemble_c3_view(
        action_context=context,
        tokens=tokens,
        token_mask=token_mask,
        action_mask=action_mask,
        reference_actions=np.full(users, action, dtype=np.int64),
    )


def _test_view_factory(action: int):
    cached = None

    def factory(**kwargs):
        # The adapter validates this immutable current C3View on every action.
        # Caching keeps the fake-environment test seconds-scale rather than
        # repeatedly allocating the 100-user structured tensor surface.
        nonlocal cached
        if cached is None:
            cached = _c3_view(kwargs["q12_snapshot"], action=action)
        return cached

    return factory


def _policies():
    from mcrl.algorithms.ee_axis_lcsrs_c3_head import LCSRSC3QNetwork
    from mcrl.algorithms.ee_axis_lcsrs_three_route import EEAxisLCSRSThreeRoute

    policies = {}
    for index, arm in enumerate(API.ARMS):
        source = EEAxisLCSRSThreeRoute(_config(), train_seed=100 + index)
        state = source.checkpoint_state(update_count=7 + index)
        model, updates = API.load_current_model_checkpoint_state(state)
        assert isinstance(model, EEAxisLCSRSThreeRoute)
        assert isinstance(model.q3, LCSRSC3QNetwork) and len(model.q_networks) == 3
        # The current class and structured C3View remain real.  Replacing only
        # its final numerical scorer gives this plumbing test an observable
        # per-arm action route without repeatedly executing the 100-user C3
        # neural scorer; numerical scorer correctness is covered by W-185.
        def route_from_current_view(_snapshot, view):
            view.verify()
            return np.asarray(view.reference_actions, dtype=np.int64)

        model.select_greedy_actions = route_from_current_view  # type: ignore[method-assign]
        binding = API.PlumbingPolicyBinding(
            arm=arm,
            checkpoint_sha256=(format(index + 10, "x")[-1]) * 64,
            update_count=updates,
            source_mapping=API.SOURCE_MAPPING[arm],
            model_algorithm=state["algorithm"],
        )
        policies[arm] = API.CurrentV023FixedPolicy(
            binding=binding,
            model=model,
            c3_view_factory=_test_view_factory(index),
        )
    return policies


class FakeTrainerEnvironment(API._physical.TrainerEnvironment):
    """Typed fake that preserves the physical runner's observable boundary."""

    def __init__(self) -> None:
        self.config = SimpleNamespace(num_users=100, steps_per_episode=10)
        self.environment = SimpleNamespace(
            _fading_field=None,
            driver=SimpleNamespace(
                config=SimpleNamespace(ephemeris=SimpleNamespace(time_step_s=0.25))
            ),
        )
        self.index = 0
        self.actions: list[np.ndarray] = []
        self._last_outcome = None

    def reset(self, *_rngs):
        self.index = 0
        self.actions = []
        return None, None, SimpleNamespace(step_index=0)

    def step(self, actions, _rng):
        self.index += 1
        self.actions.append(np.asarray(actions, dtype=np.int64).copy())
        self._last_outcome = SimpleNamespace(
            link_rate_bps=np.full(100, 4.0, dtype=np.float64),
            system_power_w=8.0,
            resolution=SimpleNamespace(served_count=70),
            observation=SimpleNamespace(step_index=self.index),
            done=self.index == 10,
        )

    @property
    def last_outcome(self):
        assert self._last_outcome is not None
        return self._last_outcome


def _native(_environment, observation):
    return SimpleNamespace(
        state_matrix=np.full((100, 228), float(observation.step_index), dtype=np.float32),
        action_masks=np.ones((100, 28), dtype=np.bool_),
    )


def test_actual_current_models_route_all_five_arms_through_one_keyed_train_world(tmp_path: Path):
    policies = _policies()
    initial_parameters = {arm: policy.parameter_sha256() for arm, policy in policies.items()}
    created: list[FakeTrainerEnvironment] = []

    def factory(_tle_root, _users):
        environment = FakeTrainerEnvironment()
        created.append(environment)
        return environment

    adapter = API.V023RealOneWorldPlumbingAdapter(
        policies=policies,
        tle_root=tmp_path,
        execute=True,
        environment_factory=factory,
        rng_factory=lambda seed: (np.random.default_rng(seed), np.random.default_rng(seed + 1)),
        encode_native_state=_native,
        trainer_environment_type=FakeTrainerEnvironment,
    )
    world = API.make_train_world(world_index=1, world_id="train-one-world-001", world_seed=2026090601)
    receipts = adapter.run_one_world(world=world)

    assert tuple(row.arm for row in receipts) == API.ARMS
    assert [policy.binding.source_mapping for policy in policies.values()] == [API.SOURCE_MAPPING[arm] for arm in API.ARMS]
    assert len({id(policy.model) for policy in policies.values()}) == 5
    assert len(created) == 5 and len({id(environment) for environment in created}) == 5
    assert {id(environment.environment._fading_field) for environment in created} == {
        id(created[0].environment._fading_field)
    }
    assert {row.field_root_digest for row in receipts} == {world.field_root_digest}
    assert {(row.world_index, row.world_id, row.world_seed) for row in receipts} == {
        (world.world_index, world.world_id, world.world_seed)
    }
    assert [int(environment.actions[0][0]) for environment in created] == list(range(5))
    assert all(len(environment.actions) == 10 for environment in created)
    assert all(policy.select_call_count == 10 for policy in policies.values())
    assert all(row.total_bits == pytest.approx(1000.0) and row.total_energy_j == pytest.approx(20.0) for row in receipts)
    assert all(row.fixed_policy and not row.learner_update and not row.episode_training for row in receipts)
    assert all(not row.test_split_opened and not row.head_drop for row in receipts)
    assert {arm: policy.parameter_sha256() for arm, policy in policies.items()} == initial_parameters


def test_rejects_d40_head_drop_test_and_missing_current_inputs_without_opening_a_world(tmp_path: Path):
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="D40"):
        API.load_current_model_checkpoint_state({"algorithm": "d40-legacy", "update_count": 1})

    with pytest.raises(API.V023RealOneWorldPlumbingError, match="head-preserving"):
        API.PlumbingPolicyBinding(
            arm="FULL",
            checkpoint_sha256="a" * 64,
            update_count=1,
            source_mapping=API.SOURCE_MAPPING["FULL"],
            model_algorithm=API._checkpoint_algorithm(),
            head_drop=True,
        )

    train_world = API.make_train_world(world_index=1, world_id="train-one-world-001", world_seed=1)
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="only TRAIN"):
        replace(train_world, split="TEST").verify()
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="provider is required"):
        API.CurrentStructuredC3ViewFactory(None)  # type: ignore[arg-type]
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="exact ALL_NEUTRAL_CONTROL"):
        API.load_current_five_arm_models({})

    with pytest.raises(API.V023RealOneWorldPlumbingError, match="execute flag"):
        API.V023RealOneWorldPlumbingAdapter(
            policies={arm: object() for arm in API.ARMS},
            tle_root=tmp_path,
            execute=False,
            environment_factory=lambda *_: FakeTrainerEnvironment(),
            rng_factory=lambda seed: (np.random.default_rng(seed), np.random.default_rng(seed + 1)),
            encode_native_state=_native,
            trainer_environment_type=FakeTrainerEnvironment,
        )

    request = API.PreflightRequest(checkpoint_paths={}, tle_root=None, execute=False)
    payload = API.preflight_payload(request)
    assert payload["physical_work_executed"] is False
    assert payload["ready_for_explicit_host_execution"] is False
    assert "five explicit checkpoints in ALL_NEUTRAL_CONTROL/FULL/DROP_C1/DROP_C2/DROP_C3 order" in payload["missing_real_inputs"]
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="--execute"):
        request.verify_for_execution()


def test_domain_separated_binding_rejects_source_remapping_and_is_not_an_evaluation_identity():
    with pytest.raises(API.V023RealOneWorldPlumbingError, match="source mapping"):
        API.PlumbingPolicyBinding(
            arm="DROP_C3",
            checkpoint_sha256="b" * 64,
            update_count=1,
            source_mapping={"C1": "informed", "C2": "informed", "C3": "informed"},
            model_algorithm=API._checkpoint_algorithm(),
        )
    binding = API.PlumbingPolicyBinding(
        arm="DROP_C3",
        checkpoint_sha256="b" * 64,
        update_count=1,
        source_mapping=API.SOURCE_MAPPING["DROP_C3"],
        model_algorithm=API._checkpoint_algorithm(),
    )
    assert binding.domain == API.PLUMBING_DOMAIN
    assert binding.schema.endswith("policy-binding")
    assert binding.to_dict()["source_mapping"] == API.SOURCE_MAPPING["DROP_C3"]
