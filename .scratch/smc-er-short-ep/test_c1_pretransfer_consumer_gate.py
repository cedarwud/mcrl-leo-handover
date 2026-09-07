from __future__ import annotations

from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "run_c1_pretransfer_consumer_gate",
    HERE / "run_c1_pretransfer_consumer_gate.py",
)
assert SPEC is not None and SPEC.loader is not None
G = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = G
SPEC.loader.exec_module(G)

from mcrl.runtime.q_network import DQNNetwork
from mcrl.runtime.trainer_spec import TrainerConfig
from smc_er_core import AtomicBundle, ConsumedBundleLedger, update_main_with_source_quota


def checkpoint() -> SimpleNamespace:
    config = TrainerConfig(
        hidden_layers=(8,),
        batch_size=2,
        episodes=1,
        learning_rate=0.001,
        reward_calibration_enabled=True,
        reward_calibration_scales=(2.0, 3.0, 4.0),
        objective_weights=(0.5, 0.3, 0.2),
    )
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(41)
        online = [DQNNetwork(4, 3, config.hidden_layers, config.activation) for _ in range(3)]
    target = [DQNNetwork(4, 3, config.hidden_layers, config.activation) for _ in range(3)]
    for target_network, online_network in zip(target, online, strict=True):
        target_network.load_state_dict(online_network.state_dict())
    return SimpleNamespace(
        trainer_config=asdict(config),
        state_dim=4,
        action_dim=3,
        q_networks=[network.state_dict() for network in online],
        target_networks=[network.state_dict() for network in target],
        optimizers=None,
    )


def bundle(bundle_id: str, source: str) -> AtomicBundle:
    states = np.arange(16, dtype=np.float32).reshape(4, 4) / 10.0
    masks = np.ones((4, 3), dtype=bool)
    return AtomicBundle(
        bundle_id=bundle_id,
        source_id=source,
        source_policy_version=0,
        block_id=0,
        step_index=0,
        states=states,
        actions=np.array([0, 1, 2, 0]),
        rewards=np.array(
            [[2.0, -1.0, -2.0], [3.0, -2.0, -1.0], [4.0, -1.0, -3.0], [5.0, -2.0, -2.0]],
            dtype=np.float64,
        ),
        next_states=states + 0.05,
        masks=masks,
        next_masks=masks,
        done=False,
        specialist_rewards=np.arange(4, dtype=np.float64) if source == "C1" else None,
        provenance={"private": source},
    )


def test_independent_atomic_reference_matches_production_update():
    authority = checkpoint()
    main_bundle = bundle("main", "Main")
    c1_bundle = bundle("c1", "C1")
    production = G.FixtureMain(authority, rng_seed=17)
    reference = G.FixtureMain(authority, rng_seed=17)
    production_losses, receipt = update_main_with_source_quota(
        production,
        [c1_bundle],
        source_quota=("C1",),
        main_bundle=main_bundle,
        consumed_ledger=ConsumedBundleLedger(),
    )
    reference_losses = G.reference_atomic_update(reference, [main_bundle, c1_bundle])
    equal, difference = G._state_close(G._snapshot(production), G._snapshot(reference))
    assert production_losses == pytest.approx(reference_losses, rel=G.RTOL, abs=G.ATOL)
    assert equal, difference
    assert receipt["source_units"] == ["Main", "C1"]


def test_private_specialist_reward_and_provenance_are_invisible_to_main():
    authority = checkpoint()
    main_bundle = bundle("main", "Main")
    canonical = bundle("c1", "C1")
    left = G._clone_bundle(
        canonical,
        specialist_rewards=np.full(4, 1e9),
        provenance={"private": "left"},
    )
    right = G._clone_bundle(
        canonical,
        specialist_rewards=np.full(4, -1e9),
        provenance={"private": "right"},
    )
    left_main = G.FixtureMain(authority, rng_seed=19)
    right_main = G.FixtureMain(authority, rng_seed=19)
    left_loss, _ = update_main_with_source_quota(
        left_main,
        [left],
        source_quota=("C1",),
        main_bundle=main_bundle,
        consumed_ledger=ConsumedBundleLedger(),
    )
    right_loss, _ = update_main_with_source_quota(
        right_main,
        [right],
        source_quota=("C1",),
        main_bundle=main_bundle,
        consumed_ledger=ConsumedBundleLedger(),
    )
    assert left_loss == right_loss
    assert G._first_difference(G._snapshot(left_main), G._snapshot(right_main)) is None


def test_noop_row_reward_cannot_change_main_update():
    authority = checkpoint()
    main_bundle = bundle("main", "Main")
    canonical = bundle("c1", "C1")
    actions = np.array(canonical.actions, copy=True)
    actions[-1] = -1
    left = G._clone_bundle(canonical, actions=actions)
    rewards = np.array(left.rewards, copy=True)
    rewards[-1] = np.array([1e12, -1e12, 1e12])
    right = G._clone_bundle(left, rewards=rewards)
    left_main = G.FixtureMain(authority, rng_seed=23)
    right_main = G.FixtureMain(authority, rng_seed=23)
    left_loss, _ = update_main_with_source_quota(
        left_main,
        [left],
        source_quota=("C1",),
        main_bundle=main_bundle,
        consumed_ledger=ConsumedBundleLedger(),
    )
    right_loss, _ = update_main_with_source_quota(
        right_main,
        [right],
        source_quota=("C1",),
        main_bundle=main_bundle,
        consumed_ledger=ConsumedBundleLedger(),
    )
    assert left_loss == right_loss
    assert G._first_difference(G._snapshot(left_main), G._snapshot(right_main)) is None


def test_preference_fixture_fails_closed_when_executed_equals_comparator():
    authority = checkpoint()
    original = bundle("c1", "C1")
    frozen = G.FixtureMain(authority, rng_seed=29)
    comparator = G._frozen_main_comparator(frozen, original, 0)
    actions = np.array(original.actions, copy=True)
    actions[0] = comparator
    matched = G._clone_bundle(original, actions=actions)
    changed_rewards = np.array(matched.rewards, copy=True)
    changed_rewards[0] += np.array([2.0, 3.0, 4.0])
    changed = G._clone_bundle(matched, rewards=changed_rewards)
    result = G._preference_perturbation_check(
        authority,
        rng_seed=29,
        main_bundle=bundle("main", "Main"),
        c1_bundle=matched,
        mutated_bundle=changed,
        focal_row=0,
    )
    assert result == {
        "informative": False,
        "reason": "the selected row equals the frozen Main comparator",
        "non_reversal": False,
    }


def test_gate_rejects_legacy_self_attested_zero_dose_pass(tmp_path):
    parity = tmp_path / "legacy-parity.json"
    parity.write_text(
        json.dumps(
            {
                "schema": "smc-er-zero-dose-parity-v1",
                "status": "PASS",
                "exact_after_descriptive_metadata_normalisation": True,
                "first_difference": None,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="authenticated exact PASS"):
        G.evaluate_gate(
            checkpoint_path=tmp_path / "unused-checkpoint.pt",
            corpus_manifest_path=tmp_path / "unused-corpus.json",
            zero_dose_parity_path=parity,
        )
