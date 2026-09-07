from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("smc_er_core", HERE / "smc_er_core.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


def bundle(bundle_id="b1", *, source="C1", focal=None, done=False):
    states = np.arange(12, dtype=np.float32).reshape(3, 4)
    masks = np.ones((3, 2), dtype=bool)
    return C.AtomicBundle(
        bundle_id=bundle_id,
        source_id=source,
        source_policy_version=0,
        block_id=0,
        step_index=0,
        states=states,
        actions=np.array([0, 1, 0]),
        rewards=np.array([[1.0, -1.0, -2.0]] * 3),
        next_states=states + 1,
        masks=masks,
        next_masks=masks,
        done=done,
        focal_user=focal,
        behavior_probabilities=np.ones(3, dtype=np.float64),
    )


def test_bundle_copies_and_freezes_complete_arrays():
    raw = np.arange(12, dtype=np.float32).reshape(3, 4)
    item = C.AtomicBundle(
        bundle_id="immutable",
        source_id="Main",
        source_policy_version=0,
        block_id=0,
        step_index=0,
        states=raw,
        actions=np.array([0, 1, 0]),
        rewards=np.zeros((3, 3)),
        next_states=raw,
        masks=np.ones((3, 2), dtype=bool),
        next_masks=np.ones((3, 2), dtype=bool),
        done=False,
    )
    raw[:] = -1
    assert item.states[0, 0] == 0
    with pytest.raises(ValueError):
        item.rewards[0, 0] = 9.0


def test_bundle_deep_freezes_json_compatible_provenance():
    item = replace(
        bundle(bundle_id="frozen-lineage"),
        provenance={"outer": {"values": [1, 2]}},
    )
    assert item.provenance["outer"]["values"] == (1, 2)
    assert json.loads(json.dumps(item.provenance)) == {
        "outer": {"values": [1, 2]}
    }
    with pytest.raises(TypeError, match="frozen provenance"):
        item.provenance["new"] = 3
    with pytest.raises(TypeError, match="frozen provenance"):
        item.provenance["outer"]["new"] = 4


def test_bundle_rejects_action_outside_decision_mask():
    masks = np.ones((3, 2), dtype=bool)
    masks[1, 1] = False
    with pytest.raises(ValueError, match="decision mask"):
        C.AtomicBundle(
            bundle_id="bad-mask",
            source_id="Main",
            source_policy_version=0,
            block_id=0,
            step_index=0,
            states=np.zeros((3, 4)),
            actions=np.array([0, 1, 0]),
            rewards=np.zeros((3, 3)),
            next_states=np.zeros((3, 4)),
            masks=masks,
            next_masks=np.ones((3, 2), dtype=bool),
            done=False,
        )


def test_bundle_replay_rejects_duplicate_even_after_sampling():
    replay = C.BundleReplay(3)
    item = bundle()
    replay.push(item)
    assert replay.sample(1, np.random.default_rng(1))[0].bundle_id == "b1"
    with pytest.raises(ValueError, match="duplicate"):
        replay.push(item)


def test_consumed_bundle_ledger_rejects_duplicate_across_calls_and_resume():
    first = C.ConsumedBundleLedger()
    item = bundle(bundle_id="durable-c1", source="C1")
    assert first.admit([item]) == ("durable-c1",)
    with pytest.raises(ValueError, match="already consumed"):
        first.admit([item])

    resumed = C.ConsumedBundleLedger()
    resumed.load_state_dict(first.state_dict())
    with pytest.raises(ValueError, match="already consumed"):
        resumed.admit([item])


def test_consumed_bundle_ledger_preflight_is_nonmutating_until_commit():
    ledger = C.ConsumedBundleLedger()
    item = bundle(bundle_id="two-phase-c2", source="C2", focal=1)
    pending = ledger.preflight([item])
    assert pending == ("two-phase-c2",)
    assert ledger.state_dict()["seen_bundle_ids"] == []
    assert ledger.commit(pending) == pending
    assert ledger.state_dict()["seen_bundle_ids"] == ["two-phase-c2"]


def test_routed_quota_fails_closed_without_durable_consumed_ledger():
    with pytest.raises(ValueError, match="consumed-bundle ledger"):
        C.update_main_with_source_quota(
            object(),
            [],
            source_quota=("C1",),
            main_bundle=bundle(bundle_id="main", source="Main"),
        )


def test_gate_ledger_is_independent_and_fails_closed_by_default():
    ledger = C.GateLedger(C1="route", C2="shadow", C3="route")
    assert ledger.routes("Main")
    assert ledger.routes("C1")
    assert not ledger.routes("C2")
    assert ledger.routes("C3")
    assert not C.GateLedger().routes("C1")


def test_acrm_is_private_formula_and_keeps_shape():
    shaped = C.acrm_rewards(
        np.array([3.0, 1.0]), np.array([1.0, 2.0]), eta=0.5
    )
    assert shaped.tolist() == pytest.approx([4.0, 0.5])


def test_c2_c3_bundle_requires_focal_user_on_specialist_update():
    from mcrl.runtime.trainer_spec import TrainerConfig

    specialist = C.ObjectiveSpecialist(
        objective_index=1,
        state_dim=4,
        action_dim=2,
        config=TrainerConfig(batch_size=1, episodes=1),
        seed=9,
    )
    with pytest.raises(ValueError, match="focal_user"):
        specialist.update_bundle(bundle(source="C2"))


def test_three_specialists_own_distinct_network_optimizer_and_rng_objects():
    from mcrl.runtime.trainer_spec import TrainerConfig

    config = TrainerConfig(batch_size=1, episodes=1)
    specialists = [
        C.ObjectiveSpecialist(
            objective_index=index,
            state_dim=4,
            action_dim=2,
            config=config,
            seed=100 + index,
        )
        for index in range(3)
    ]
    assert len({id(item.online) for item in specialists}) == 3
    assert len({id(item.optimizer) for item in specialists}) == 3
    assert len({id(item.rng) for item in specialists}) == 3
    assert len({id(item.replay_rng) for item in specialists}) == 3
    assert all(item.rng is not item.replay_rng for item in specialists)
    assert all(len(list(item.online.parameters())) > 0 for item in specialists)


def test_specialist_updates_only_its_declared_focal_row():
    from mcrl.runtime.trainer_spec import TrainerConfig

    config = TrainerConfig(
        hidden_layers=(4,), batch_size=1, episodes=1, learning_rate=0.001
    )
    specialist = C.ObjectiveSpecialist(
        objective_index=2,
        state_dim=4,
        action_dim=2,
        config=config,
        seed=11,
    )
    item = bundle(source="C3", focal=1, done=True)
    before = [parameter.detach().clone() for parameter in specialist.online.parameters()]
    loss = specialist.update_bundle(item)
    after = list(specialist.online.parameters())
    assert loss >= 0.0
    assert any(not np.array_equal(a.numpy(), b.detach().numpy()) for a, b in zip(before, after))


def test_specialist_reports_marginal_epsilon_greedy_probability():
    from mcrl.runtime.trainer_spec import TrainerConfig

    specialist = C.ObjectiveSpecialist(
        objective_index=0,
        state_dim=4,
        action_dim=2,
        config=TrainerConfig(hidden_layers=(4,), episodes=1),
        seed=31,
    )
    specialist.q_values = lambda _states: np.array([[2.0, 1.0]])
    selected, probability = specialist.select_row(
        np.zeros(4), (0, 1), epsilon=0.0, informed=True
    )
    assert selected == 0
    assert probability == 1.0
    _, neutral_probability = specialist.select_row(
        np.zeros(4), (0, 1), epsilon=0.3, informed=False
    )
    assert neutral_probability == 0.5


def test_main_source_quota_zero_specialists_delegates_exact_baseline_update():
    class Main:
        def __init__(self):
            self.calls = 0

        def update(self):
            self.calls += 1
            return (1.0, 2.0, 3.0)

    main = Main()
    losses, receipt = C.update_main_with_source_quota(main, [])
    assert losses == (1.0, 2.0, 3.0)
    assert main.calls == 1
    assert receipt["mode"] == "exact_baseline_delegate"


def test_main_source_quota_rejects_main_bundle_as_specialist_input():
    with pytest.raises(ValueError, match="Main-origin"):
        C.update_main_with_source_quota(object(), [bundle(source="Main")])


def test_routed_warmup_defers_bundle_without_optimizer_or_replay_rng_sample():
    class Replay:
        def __len__(self):
            return 100

        def sample(self, _count, _rng):
            raise AssertionError("warmup must not sample canonical replay")

    class Main:
        def __init__(self):
            from mcrl.runtime.trainer_spec import TrainerConfig

            self.config = TrainerConfig(batch_size=128, episodes=1)
            self.replay = Replay()

    ledger = C.ConsumedBundleLedger()
    specialist = bundle(bundle_id="warmup-c1", source="C1")
    losses, receipt = C.update_main_with_source_quota(
        Main(),
        [specialist],
        source_quota=("C1",),
        main_bundle=bundle(bundle_id="warmup-main", source="Main"),
        consumed_ledger=ledger,
    )

    assert losses == (0.0, 0.0, 0.0)
    assert receipt["mode"] == "warmup_no_update"
    assert receipt["specialist_bundle_ids"] == []
    assert receipt["admitted_specialist_bundle_ids"] == []
    assert receipt["deferred_specialist_bundle_ids"] == ["warmup-c1"]
    assert receipt["main_replay_size_before_update"] == 100
    assert receipt["main_batch_size"] == 128
    assert receipt["canonical_replay_rng_sample_consumed"] is False
    assert ledger.state_dict()["seen_bundle_ids"] == []
    assert ledger.admit([specialist]) == ("warmup-c1",)


def test_main_source_quota_keeps_unusable_lane_as_zero_gradient_unit():
    import torch

    class Replay:
        def __len__(self):
            return 1

        def sample(self, _count, _rng):
            return (
                np.zeros((1, 4), dtype=np.float32),
                np.zeros(1, dtype=np.int64),
                np.zeros((1, 3), dtype=np.float64),
                np.zeros((1, 4), dtype=np.float32),
                np.ones((1, 2), dtype=bool),
                np.ones((1, 2), dtype=bool),
                np.ones(1, dtype=bool),
            )

    class Main:
        def __init__(self):
            from mcrl.runtime.q_network import DQNNetwork
            from mcrl.runtime.trainer_spec import TrainerConfig

            self.config = TrainerConfig(
                hidden_layers=(4,), batch_size=1, episodes=1
            )
            self.device = torch.device("cpu")
            self.q_nets = torch.nn.ModuleList(
                [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
            )
            self.target_nets = torch.nn.ModuleList(
                [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
            )
            self.optimizers = [
                torch.optim.SGD(net.parameters(), lr=0.01)
                for net in self.q_nets
            ]
            self.replay = Replay()
            self._train_rng = np.random.default_rng(1)

    unusable = bundle(bundle_id="empty", source="C2", focal=0, done=False)
    object.__setattr__(
        unusable,
        "actions",
        C._immutable_array([-1, -1, -1], dtype=np.int64),
    )
    main = Main()
    losses, receipt = C.update_main_with_source_quota(
        main,
        [unusable],
        main_bundle=bundle(bundle_id="main", source="Main"),
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    assert all(np.isfinite(loss) for loss in losses)
    assert receipt["source_units"] == ["Main", "C2"]
    assert receipt["requested_source_units"] == ["Main", "C2"]
    assert receipt["specialist_bundle_ids"] == ["empty"]
    assert receipt["unusable_specialist_bundle_ids"] == ["empty"]
    assert receipt["shortage_rule"] == "zero_gradient_source_unit"


def test_main_source_quota_keeps_missing_routed_lane_in_denominator():
    import torch

    class Replay:
        def __len__(self):
            return 1

        def sample(self, _count, _rng):
            return (
                np.zeros((1, 4), dtype=np.float32),
                np.zeros(1, dtype=np.int64),
                np.zeros((1, 3), dtype=np.float64),
                np.zeros((1, 4), dtype=np.float32),
                np.ones((1, 2), dtype=bool),
                np.ones((1, 2), dtype=bool),
                np.ones(1, dtype=bool),
            )

    class Main:
        def __init__(self):
            from mcrl.runtime.q_network import DQNNetwork
            from mcrl.runtime.trainer_spec import TrainerConfig

            self.config = TrainerConfig(
                hidden_layers=(4,), batch_size=1, episodes=1
            )
            self.device = torch.device("cpu")
            self.q_nets = torch.nn.ModuleList(
                [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
            )
            self.target_nets = torch.nn.ModuleList(
                [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
            )
            self.optimizers = [
                torch.optim.SGD(net.parameters(), lr=0.01)
                for net in self.q_nets
            ]
            self.replay = Replay()
            self._train_rng = np.random.default_rng(1)

    losses, receipt = C.update_main_with_source_quota(
        Main(),
        [],
        source_quota=("C2",),
        main_bundle=bundle(bundle_id="main", source="Main"),
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    assert all(np.isfinite(loss) for loss in losses)
    assert receipt["source_units"] == ["Main", "C2"]
    assert receipt["missing_source_ids"] == ["C2"]
    assert receipt["specialist_bundle_ids"] == []
    assert receipt["unit_definition"] == "one_complete_atomic_bundle_per_source"


def test_main_consumer_is_invariant_to_c1_private_reward_and_provenance():
    """Main must see only the canonical bundle, never ACRM/private metadata."""

    import copy
    import torch

    from check_zero_dose_parity import _first_difference
    from mcrl.runtime.q_network import DQNNetwork
    from mcrl.runtime.trainer_spec import TrainerConfig

    class Replay:
        def __len__(self):
            return 1

        def sample(self, _count, rng):
            rng.integers(0, 2**31)
            return ()

    class Main:
        def __init__(self):
            self.config = TrainerConfig(
                hidden_layers=(4,), batch_size=1, episodes=1, learning_rate=0.001
            )
            self.device = torch.device("cpu")
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(991)
                self.q_nets = torch.nn.ModuleList(
                    [DQNNetwork(4, 2, (4,), "relu") for _ in range(3)]
                )
            self.target_nets = copy.deepcopy(self.q_nets)
            self.optimizers = [
                torch.optim.Adam(net.parameters(), lr=0.001)
                for net in self.q_nets
            ]
            self.replay = Replay()
            self._train_rng = np.random.default_rng(44)

    canonical = bundle(bundle_id="c1-private-invariance", source="C1", done=True)
    private = C.AtomicBundle(
        bundle_id=canonical.bundle_id,
        source_id=canonical.source_id,
        source_policy_version=canonical.source_policy_version,
        block_id=canonical.block_id,
        step_index=canonical.step_index,
        states=canonical.states,
        actions=canonical.actions,
        rewards=canonical.rewards,
        next_states=canonical.next_states,
        masks=canonical.masks,
        next_masks=canonical.next_masks,
        done=canonical.done,
        specialist_rewards=np.asarray([99.0, -50.0, 12.0]),
        provenance={"acrm": "deliberately different", "hidden_trigger": True},
    )
    left = Main()
    right = Main()
    left_losses, left_receipt = C.update_main_with_source_quota(
        left,
        [canonical],
        source_quota=("C1",),
        main_bundle=bundle(bundle_id="main-private-left", source="Main", done=True),
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    right_losses, right_receipt = C.update_main_with_source_quota(
        right,
        [private],
        source_quota=("C1",),
        main_bundle=bundle(bundle_id="main-private-right", source="Main", done=True),
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert left_losses == right_losses
    assert left_receipt["source_units"] == right_receipt["source_units"]
    assert left._train_rng.bit_generator.state == right._train_rng.bit_generator.state
    for left_net, right_net in zip(left.q_nets, right.q_nets, strict=True):
        for key in left_net.state_dict():
            assert torch.equal(left_net.state_dict()[key], right_net.state_dict()[key])
    for left_optimizer, right_optimizer in zip(
        left.optimizers, right.optimizers, strict=True
    ):
        assert (
            _first_difference(
                left_optimizer.state_dict(), right_optimizer.state_dict()
            )
            is None
        )


class _CanonicalBatchReplay:
    def __init__(self, rewards):
        self.rewards = np.asarray(rewards, dtype=np.float32)
        self.sample_calls = []

    def __len__(self):
        return self.rewards.shape[0]

    def sample(self, count, rng):
        self.sample_calls.append((count, rng))
        rows = self.rewards.shape[0]
        states = np.arange(rows * 4, dtype=np.float32).reshape(rows, 4) / 10.0
        return (
            states,
            np.arange(rows, dtype=np.int64) % 2,
            self.rewards.copy(),
            states + 0.25,
            np.ones((rows, 2), dtype=bool),
            np.ones((rows, 2), dtype=bool),
            np.ones(rows, dtype=np.float32),
        )


class _RoleTargetedMain:
    def __init__(self, rewards):
        import copy
        import torch

        from mcrl.runtime.trainer_spec import TrainerConfig

        self.config = TrainerConfig(
            batch_size=len(rewards),
            episodes=1,
            learning_rate=0.05,
            reward_calibration_enabled=False,
        )
        self.device = torch.device("cpu")
        self.q_nets = torch.nn.ModuleList(
            [torch.nn.Linear(4, 2, bias=False) for _ in range(3)]
        )
        for net in self.q_nets:
            torch.nn.init.zeros_(net.weight)
        self.target_nets = copy.deepcopy(self.q_nets)
        self.optimizers = [
            torch.optim.SGD(net.parameters(), lr=0.05) for net in self.q_nets
        ]
        self._loss_fn = torch.nn.MSELoss()
        self.replay = _CanonicalBatchReplay(rewards)
        self._train_rng = np.random.default_rng(712)

    def update(self):
        from mcrl.algorithms.modqn import MODQNTrainer

        return MODQNTrainer.update(self)


def _network_bytes(main, objective):
    import torch

    return {
        key: value.detach().clone()
        for key, value in main.q_nets[objective].state_dict().items()
    }


def test_role_targeted_zero_dose_is_exact_canonical_delegate():
    class Main:
        def __init__(self):
            self.calls = 0

        def update(self):
            self.calls += 1
            return (4.0, 5.0, 6.0)

    main = Main()
    losses, receipt = C.update_main_with_role_targeted_donors(main, [])

    assert losses == (4.0, 5.0, 6.0)
    assert main.calls == 1
    assert receipt["mode"] == "exact_baseline_delegate"
    assert receipt["canonical_replay_sample_used"] is None


def test_role_targeted_warmup_defers_without_burning_donor_ledger():
    class Replay:
        def __len__(self):
            return 1

        def sample(self, _count, _rng):
            raise AssertionError("warmup must not sample canonical replay")

    class WarmupMain:
        def __init__(self):
            from mcrl.runtime.trainer_spec import TrainerConfig

            self.config = TrainerConfig(batch_size=2, episodes=1)
            self.replay = Replay()

    ledger = C.ConsumedBundleLedger()
    donor = bundle(bundle_id="role-warmup-c3", source="C3", focal=2, done=True)
    losses, receipt = C.update_main_with_role_targeted_donors(
        WarmupMain(),
        [donor],
        source_quota=("C3",),
        consumed_ledger=ledger,
    )

    assert losses == (0.0, 0.0, 0.0)
    assert receipt["mode"] == "warmup_no_update"
    assert receipt["scheduled_beta"] == {"C3": 0.25}
    assert receipt["effective_beta"] == {"C3": 0.0}
    assert receipt["admitted_specialist_bundle_ids"] == []
    assert receipt["deferred_specialist_bundle_ids"] == ["role-warmup-c3"]
    assert ledger.state_dict()["seen_bundle_ids"] == []

    # The exact same donor remains admissible when Main can actually update.
    _, learned_receipt = C.update_main_with_role_targeted_donors(
        _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        [donor],
        source_quota=("C3",),
        consumed_ledger=ledger,
    )
    assert learned_receipt["admitted_specialist_bundle_ids"] == ["role-warmup-c3"]
    assert learned_receipt["deferred_specialist_bundle_ids"] == []
    assert ledger.state_dict()["seen_bundle_ids"] == ["role-warmup-c3"]


def test_frozen_lineage_round_trips_through_torch_without_becoming_mutable(
    tmp_path,
):
    import torch

    lineage = C._freeze_lineage({"outer": {"value": 3}, "items": [1, 2]})
    target = tmp_path / "frozen-lineage.pt"
    torch.save({"lineage": lineage}, target)

    restored = torch.load(target, map_location="cpu", weights_only=False)[
        "lineage"
    ]
    assert restored == lineage
    assert isinstance(restored, C.FrozenDict)
    assert isinstance(restored["outer"], C.FrozenDict)
    with pytest.raises(TypeError, match="cannot be mutated"):
        restored["new"] = 4


def test_role_targeted_optimizer_failure_does_not_commit_donor_ledger():
    class FailingOptimizer:
        def __init__(self, wrapped):
            self.wrapped = wrapped

        def zero_grad(self):
            self.wrapped.zero_grad()

        def step(self):
            raise RuntimeError("injected optimizer failure")

    main = _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    main.optimizers[1] = FailingOptimizer(main.optimizers[1])
    ledger = C.ConsumedBundleLedger()
    donor = bundle(bundle_id="failed-update-c1", source="C1", done=True)

    with pytest.raises(RuntimeError, match="injected optimizer failure"):
        C.update_main_with_role_targeted_donors(
            main,
            [donor],
            source_quota=("C1",),
            consumed_ledger=ledger,
        )
    assert ledger.state_dict()["seen_bundle_ids"] == []


def test_role_targeted_update_uses_values_from_canonical_sample():
    import torch

    low = _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    high = _RoleTargetedMain([[4.0, 5.0, 6.0], [4.0, 5.0, 6.0]])
    donor = bundle(bundle_id="canonical-sample-donor", source="C1", done=True)

    low_losses, low_receipt = C.update_main_with_role_targeted_donors(
        low,
        [donor],
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    high_losses, high_receipt = C.update_main_with_role_targeted_donors(
        high,
        [donor],
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert low.replay.sample_calls == [(2, low._train_rng)]
    assert high.replay.sample_calls == [(2, high._train_rng)]
    assert low_receipt["canonical_sample_used_in_all_objective_losses"] is True
    assert high_receipt["canonical_sample_used_in_all_objective_losses"] is True
    assert low_receipt["canonical_main_losses"] != high_receipt["canonical_main_losses"]
    assert low_losses != high_losses
    assert any(
        not torch.equal(low.q_nets[index].weight, high.q_nets[index].weight)
        for index in range(3)
    )


def test_c1_reward_perturbation_changes_only_q1():
    import torch

    canonical = _RoleTargetedMain([[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]])
    perturbed = _RoleTargetedMain([[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]])
    base = bundle(bundle_id="c1-base", source="C1", done=True)
    changed_rewards = np.array(base.rewards, copy=True)
    changed_rewards[:, 0] += 9.0
    changed = C.AtomicBundle(
        bundle_id="c1-changed",
        source_id="C1",
        source_policy_version=base.source_policy_version,
        block_id=base.block_id,
        step_index=base.step_index,
        states=base.states,
        actions=base.actions,
        rewards=changed_rewards,
        next_states=base.next_states,
        masks=base.masks,
        next_masks=base.next_masks,
        done=base.done,
        behavior_probabilities=base.behavior_probabilities,
    )

    base_losses, _ = C.update_main_with_role_targeted_donors(
        canonical,
        [base],
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    changed_losses, _ = C.update_main_with_role_targeted_donors(
        perturbed,
        [changed],
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert not torch.equal(canonical.q_nets[0].weight, perturbed.q_nets[0].weight)
    assert base_losses[0] != changed_losses[0]
    for objective in (1, 2):
        assert torch.equal(
            canonical.q_nets[objective].weight,
            perturbed.q_nets[objective].weight,
        )
        assert base_losses[objective] == changed_losses[objective]


@pytest.mark.parametrize(
    ("source", "target_objective", "focal"),
    [("C1", 0, None), ("C2", 1, 1), ("C3", 2, 2)],
)
def test_each_role_reward_perturbation_changes_only_matching_q(
    source, target_objective, focal
):
    import torch

    rewards = [[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]]
    canonical = _RoleTargetedMain(rewards)
    perturbed = _RoleTargetedMain(rewards)
    base = bundle(
        bundle_id=f"{source.lower()}-base",
        source=source,
        focal=focal,
        done=True,
    )
    changed_rewards = np.array(base.rewards, copy=True)
    changed_rewards[:, target_objective] += 9.0
    changed = C.AtomicBundle(
        bundle_id=f"{source.lower()}-changed",
        source_id=source,
        source_policy_version=base.source_policy_version,
        block_id=base.block_id,
        step_index=base.step_index,
        states=base.states,
        actions=base.actions,
        rewards=changed_rewards,
        next_states=base.next_states,
        masks=base.masks,
        next_masks=base.next_masks,
        done=base.done,
        focal_user=focal,
        behavior_probabilities=base.behavior_probabilities,
    )

    base_losses, _ = C.update_main_with_role_targeted_donors(
        canonical,
        [base],
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    changed_losses, _ = C.update_main_with_role_targeted_donors(
        perturbed,
        [changed],
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    for objective in range(3):
        if objective == target_objective:
            assert not torch.equal(
                canonical.q_nets[objective].weight,
                perturbed.q_nets[objective].weight,
            )
            assert base_losses[objective] != changed_losses[objective]
        else:
            assert torch.equal(
                canonical.q_nets[objective].weight,
                perturbed.q_nets[objective].weight,
            )
            assert base_losses[objective] == changed_losses[objective]


def test_missing_scheduled_role_is_exact_canonical_update_without_dose_borrowing():
    from check_zero_dose_parity import _first_difference

    import torch

    rewards = [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]]
    canonical = _RoleTargetedMain(rewards)
    scheduled = _RoleTargetedMain(rewards)

    canonical_losses = canonical.update()
    scheduled_losses, receipt = C.update_main_with_role_targeted_donors(
        scheduled,
        [],
        source_quota=("C1",),
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert scheduled_losses == canonical_losses
    assert receipt["effective_beta"] == {"C1": 0.0}
    assert receipt["missing_source_ids"] == ["C1"]
    assert receipt["dose_borrowing"] is False
    assert (
        scheduled._train_rng.bit_generator.state
        == canonical._train_rng.bit_generator.state
    )
    assert [count for count, _rng in scheduled.replay.sample_calls] == [
        count for count, _rng in canonical.replay.sample_calls
    ]
    assert all(
        rng is scheduled._train_rng for _count, rng in scheduled.replay.sample_calls
    )
    assert all(
        rng is canonical._train_rng for _count, rng in canonical.replay.sample_calls
    )
    for objective in range(3):
        for key, expected in canonical.q_nets[objective].state_dict().items():
            assert torch.equal(expected, scheduled.q_nets[objective].state_dict()[key])
        assert (
            _first_difference(
                canonical.optimizers[objective].state_dict(),
                scheduled.optimizers[objective].state_dict(),
            )
            is None
        )


def test_role_targeted_main_ignores_c1_private_fields():
    import torch

    left = _RoleTargetedMain([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
    right = _RoleTargetedMain([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
    canonical = bundle(bundle_id="private-canonical", source="C1", done=True)
    private = C.AtomicBundle(
        bundle_id="private-mutated",
        source_id="C1",
        source_policy_version=canonical.source_policy_version,
        block_id=canonical.block_id,
        step_index=canonical.step_index,
        states=canonical.states,
        actions=canonical.actions,
        rewards=canonical.rewards,
        next_states=canonical.next_states,
        masks=canonical.masks,
        next_masks=canonical.next_masks,
        done=canonical.done,
        specialist_rewards=np.array([500.0, -800.0, 99.0]),
        behavior_probabilities=canonical.behavior_probabilities,
        provenance={"private": "must not enter Main"},
    )

    left_losses, left_receipt = C.update_main_with_role_targeted_donors(
        left,
        [canonical],
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    right_losses, right_receipt = C.update_main_with_role_targeted_donors(
        right,
        [private],
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert left_losses == right_losses
    assert (
        left_receipt["donor_loss_audit"]["C1"]["canonical_rewards_sha256"]
        == right_receipt["donor_loss_audit"]["C1"]["canonical_rewards_sha256"]
    )
    assert right_receipt["private_specialist_fields_ignored"] == [
        "specialist_rewards",
        "provenance",
    ]
    for objective in range(3):
        assert all(
            torch.equal(left_value, right.q_nets[objective].state_dict()[key])
            for key, left_value in _network_bytes(left, objective).items()
        )


def test_role_targeted_source_mapping_and_audit_receipt():
    main = _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    donors = [
        bundle(bundle_id="mapped-c1", source="C1", done=True),
        bundle(bundle_id="mapped-c2", source="C2", focal=1, done=True),
        bundle(bundle_id="mapped-c3", source="C3", focal=2, done=True),
    ]

    _, receipt = C.update_main_with_role_targeted_donors(
        main,
        donors,
        source_quota=("C1", "C2", "C3"),
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert receipt["role_to_objective"] == {"C1": 0, "C2": 1, "C3": 2}
    assert receipt["scheduled_beta"] == {"C1": 0.25, "C2": 0.25, "C3": 0.25}
    assert receipt["effective_beta"] == {"C1": 0.25, "C2": 0.25, "C3": 0.25}
    assert receipt["missing_source_ids"] == []
    assert receipt["unusable_specialist_bundle_ids"] == []
    assert receipt["canonical_replay_reward_space"] == (
        "precalibrated_at_main_admission"
    )
    assert receipt["donor_reward_space"] == (
        "canonical_raw_then_main_calibration_once"
    )
    expected_rows = {
        "C1": {
            "policy": "all_admissible_joint_rows",
            "target": [0, 1, 2],
            "nonfocal": [],
        },
        "C2": {
            "policy": "focal_row_only",
            "target": [1],
            "nonfocal": [0, 2],
        },
        "C3": {
            "policy": "focal_row_only",
            "target": [2],
            "nonfocal": [0, 1],
        },
    }
    for source, target in receipt["role_to_objective"].items():
        audit = receipt["donor_loss_audit"][source]
        assert audit["target_objective"] == target
        assert audit["target_loss"] is not None
        assert audit["source_block_id"] == 0
        assert audit["consumer_block_id"] == 0
        assert audit["source_age_blocks"] == 0
        assert audit["behavior_probabilities"] == [
            1.0 for _ in expected_rows[source]["target"]
        ]
        assert audit["donor_row_policy"] == expected_rows[source]["policy"]
        assert audit["target_rows"] == expected_rows[source]["target"]
        assert audit["nonfocal_audit_rows"] == expected_rows[source]["nonfocal"]
        assert (audit["nonfocal_target_loss_no_grad"] is not None) == (
            source in {"C2", "C3"}
        )
        assert set(audit["no_grad_audit_losses"]) == {
            str(index) for index in range(3) if index != target
        }


@pytest.mark.parametrize(("source", "target_objective", "focal"), [("C2", 1, 1), ("C3", 2, 2)])
def test_c2_c3_nonfocal_rows_are_audit_only(source, target_objective, focal):
    import torch

    canonical = _RoleTargetedMain([[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]])
    perturbed = _RoleTargetedMain([[0.5, 0.5, 0.5], [0.25, 0.25, 0.25]])
    base = bundle(
        bundle_id=f"{source.lower()}-nonfocal-base",
        source=source,
        focal=focal,
        done=True,
    )
    changed_rewards = np.array(base.rewards, copy=True)
    nonfocal = [uid for uid in range(base.users) if uid != focal]
    changed_rewards[nonfocal, target_objective] += 99.0
    changed_states = np.array(base.states, copy=True)
    changed_states[nonfocal] += 50.0
    changed = C.AtomicBundle(
        bundle_id=f"{source.lower()}-nonfocal-changed",
        source_id=source,
        source_policy_version=base.source_policy_version,
        block_id=base.block_id,
        step_index=base.step_index,
        states=changed_states,
        actions=base.actions,
        rewards=changed_rewards,
        next_states=base.next_states,
        masks=base.masks,
        next_masks=base.next_masks,
        done=base.done,
        focal_user=focal,
        behavior_probabilities=base.behavior_probabilities,
    )

    base_losses, base_receipt = C.update_main_with_role_targeted_donors(
        canonical,
        [base],
        consumed_ledger=C.ConsumedBundleLedger(),
    )
    changed_losses, changed_receipt = C.update_main_with_role_targeted_donors(
        perturbed,
        [changed],
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert base_losses == changed_losses
    for objective in range(3):
        assert all(
            torch.equal(value, perturbed.q_nets[objective].state_dict()[key])
            for key, value in canonical.q_nets[objective].state_dict().items()
        )
    base_audit = base_receipt["donor_loss_audit"][source]
    changed_audit = changed_receipt["donor_loss_audit"][source]
    assert base_audit["target_rows"] == [focal]
    assert changed_audit["target_rows"] == [focal]
    assert base_audit["target_loss"] == changed_audit["target_loss"]
    assert (
        base_audit["nonfocal_target_loss_no_grad"]
        != changed_audit["nonfocal_target_loss_no_grad"]
    )


@pytest.mark.parametrize("source", ["C2", "C3"])
def test_role_targeted_rejects_c2_c3_without_focal_authority(source):
    donor = bundle(bundle_id=f"{source.lower()}-missing-focal", source=source)
    with pytest.raises(ValueError, match="focal-row authority"):
        C.update_main_with_role_targeted_donors(
            _RoleTargetedMain([[0.0, 0.0, 0.0]]),
            [donor],
            consumed_ledger=C.ConsumedBundleLedger(),
        )


def test_role_targeted_missing_or_unusable_source_has_zero_beta_without_borrowing():
    main = _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    unusable = bundle(bundle_id="unusable-c2", source="C2", focal=0)
    object.__setattr__(
        unusable,
        "actions",
        C._immutable_array([-1, -1, -1], dtype=np.int64),
    )

    _, receipt = C.update_main_with_role_targeted_donors(
        main,
        [unusable],
        source_quota=("C1", "C2", "C3"),
        consumed_ledger=C.ConsumedBundleLedger(),
    )

    assert receipt["effective_beta"] == {"C1": 0.0, "C2": 0.0, "C3": 0.0}
    assert receipt["missing_source_ids"] == ["C1", "C3"]
    assert receipt["unusable_specialist_bundle_ids"] == ["unusable-c2"]
    assert receipt["dose_borrowing"] is False


def test_role_targeted_rejects_missing_behavior_probability_authority():
    item = replace(
        bundle(bundle_id="missing-behavior", source="C1"),
        behavior_probabilities=None,
    )
    with pytest.raises(ValueError, match="behavior-probability authority"):
        C.update_main_with_role_targeted_donors(
            object(),
            [item],
            source_quota=("C1",),
            consumed_ledger=C.ConsumedBundleLedger(),
        )


def test_role_targeted_rejects_future_source_block():
    item = replace(bundle(bundle_id="future-source", source="C1"), block_id=2)
    with pytest.raises(ValueError, match="future consumer block"):
        C.update_main_with_role_targeted_donors(
            object(),
            [item],
            source_quota=("C1",),
            consumed_ledger=C.ConsumedBundleLedger(),
            consumer_block_id=1,
        )


def test_role_targeted_duplicate_validation_and_durable_ledger():
    item = bundle(bundle_id="role-duplicate", source="C1", done=True)
    with pytest.raises(ValueError, match="same specialist bundle"):
        C.update_main_with_role_targeted_donors(object(), [item, item])
    with pytest.raises(ValueError, match="cannot repeat"):
        C.update_main_with_role_targeted_donors(
            object(), [], source_quota=("C1", "C1")
        )
    with pytest.raises(ValueError, match="at most one bundle per source"):
        C.update_main_with_role_targeted_donors(
            object(),
            [item, bundle(bundle_id="role-duplicate-2", source="C1")],
            source_quota=("C1",),
        )

    ledger = C.ConsumedBundleLedger()
    C.update_main_with_role_targeted_donors(
        _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        [item],
        consumed_ledger=ledger,
    )
    resumed = C.ConsumedBundleLedger()
    resumed.load_state_dict(ledger.state_dict())
    with pytest.raises(ValueError, match="already consumed"):
        C.update_main_with_role_targeted_donors(
            _RoleTargetedMain([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]),
            [item],
            consumed_ledger=resumed,
        )


@pytest.mark.parametrize("beta", [-0.01, 1.0, float("nan"), float("inf")])
def test_role_targeted_beta_validation(beta):
    with pytest.raises(ValueError, match="0 <= beta < 1"):
        C.update_main_with_role_targeted_donors(object(), [], beta=beta)
