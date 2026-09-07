"""W-42 — V0.3 C1/C3 opening-pair production and route isolation."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mcrl.algorithms.ee_axis_pairwise import (
    EEAxisPairwiseConfig,
    EEAxisPairwiseTrainer,
)
from mcrl.runtime.ee_axis_opening_pairs import (
    OpeningPairContractError,
    build_opening_pair,
    build_opening_route_batch,
    update_opening_route,
)


def _pair(route: str = "C1", *, multiplier: float = 10.0):
    return build_opening_pair(
        source_route=route,
        source_rule="test-sealed-source",
        source_policy_version=1,
        anchor_sha256="a" * 64,
        source_manifest_sha256="b" * 64,
        checkpoint_sha256="c" * 64,
        common_random_field_sha256="d" * 64,
        focal_user=1,
        state=np.asarray([0.25, -0.5], dtype=np.float32),
        action_mask=np.asarray([True, True, True], dtype=np.bool_),
        reference_action=0,
        candidate_action=2,
        reference_joint_actions=np.asarray([1, 0, -1], dtype=np.int64),
        candidate_joint_actions=np.asarray([1, 2, -1], dtype=np.int64),
        reference_rates_bps=np.asarray([100.0, 50.0, 25.0]),
        candidate_rates_bps=np.asarray([110.0, 80.0, 20.0]),
        reference_system_power_w=10.0,
        candidate_system_power_w=12.0,
        lambda_bits_per_j=multiplier,
        interval_s=2.0,
    )


def test_c1_and_c3_share_raw_comparison_but_route_different_targets() -> None:
    c1 = _pair("C1")
    c3 = _pair("C3")

    # C1 = focal rate change (30 bit/s) * 2 s - lambda * 4 J.
    assert c1.zeta1_focal_surplus_bits == pytest.approx(20.0)
    # C3 = non-focal rate changes ((10 - 5) bit/s) * 2 s.
    assert c1.zeta3_nonfocal_externality_bits == pytest.approx(10.0)
    assert c1.route_target_surplus_bits == pytest.approx(20.0)
    assert c3.route_target_surplus_bits == pytest.approx(10.0)
    assert c1.identity_residual_bits == pytest.approx(0.0)
    assert c1.comparison_sha256 != c3.comparison_sha256


def test_c3_target_is_multiplier_invariant_while_c1_is_not() -> None:
    low_c1 = _pair("C1", multiplier=5.0)
    high_c1 = _pair("C1", multiplier=20.0)
    low_c3 = _pair("C3", multiplier=5.0)
    high_c3 = _pair("C3", multiplier=20.0)

    assert low_c1.route_target_surplus_bits != high_c1.route_target_surplus_bits
    assert low_c3.route_target_surplus_bits == high_c3.route_target_surplus_bits


def test_opening_pair_requires_exactly_one_focal_action_change() -> None:
    kwargs = dict(_pair("C1").__dict__)
    for field in (
        "zeta1_focal_surplus_bits",
        "zeta3_nonfocal_externality_bits",
        "route_target_surplus_bits",
        "identity_residual_bits",
        "comparison_sha256",
    ):
        kwargs.pop(field)
    kwargs["candidate_joint_actions"] = np.asarray([0, 2, -1], dtype=np.int64)

    with pytest.raises(OpeningPairContractError, match="only in the focal"):
        build_opening_pair(**kwargs)


def test_opening_pair_requires_legal_distinct_focal_actions() -> None:
    kwargs = dict(_pair("C1").__dict__)
    for field in (
        "zeta1_focal_surplus_bits",
        "zeta3_nonfocal_externality_bits",
        "route_target_surplus_bits",
        "identity_residual_bits",
        "comparison_sha256",
    ):
        kwargs.pop(field)
    kwargs["action_mask"] = np.asarray([True, True, False], dtype=np.bool_)

    with pytest.raises(OpeningPairContractError, match="candidate_action"):
        build_opening_pair(**kwargs)


def test_route_batch_rejects_c1_c3_mixing_and_binds_digest() -> None:
    with pytest.raises(OpeningPairContractError, match="cannot mix"):
        build_opening_route_batch([_pair("C1"), _pair("C3")])

    batch = build_opening_route_batch([_pair("C1"), _pair("C1")])
    assert batch.route == "C1"
    assert batch.pair_batch.states.shape == (2, 2)
    assert batch.pair_batch.target_surplus_bits.tolist() == [20.0, 20.0]
    assert batch.verify() == batch.batch_sha256


def test_pair_and_batch_digests_fail_closed() -> None:
    pair = _pair("C1")
    with pytest.raises(OpeningPairContractError, match="digest disagrees"):
        replace(pair, route_target_surplus_bits=999.0).verify()

    batch = build_opening_route_batch([pair])
    with pytest.raises(OpeningPairContractError, match="batch digest"):
        replace(batch, batch_sha256="f" * 64).verify()

    tampered_targets = batch.pair_batch.target_surplus_bits.copy()
    tampered_targets[0] = 777.0
    tampered_pair_batch = replace(
        batch.pair_batch, target_surplus_bits=tampered_targets
    )
    with pytest.raises(OpeningPairContractError, match="batch digest"):
        replace(batch, pair_batch=tampered_pair_batch).verify()


def test_arrays_are_immutable_and_raw_physics_is_retained() -> None:
    pair = _pair("C1")
    assert pair.reference_rates_bps.tolist() == [100.0, 50.0, 25.0]
    assert pair.candidate_system_power_w == 12.0
    assert not pair.state.flags.writeable
    assert not pair.action_mask.flags.writeable
    with pytest.raises(ValueError):
        pair.state[0] = 1.0

    batch = build_opening_route_batch([pair])
    assert not batch.pair_batch.states.flags.writeable
    assert not batch.pair_batch.target_surplus_bits.flags.writeable


def test_mask_and_joint_action_dtypes_fail_closed() -> None:
    kwargs = dict(_pair("C1").__dict__)
    for field in (
        "zeta1_focal_surplus_bits",
        "zeta3_nonfocal_externality_bits",
        "route_target_surplus_bits",
        "identity_residual_bits",
        "comparison_sha256",
    ):
        kwargs.pop(field)
    kwargs["action_mask"] = np.asarray([1, 1, 1], dtype=np.int64)
    with pytest.raises(OpeningPairContractError, match="Boolean dtype"):
        build_opening_pair(**kwargs)

    kwargs["action_mask"] = np.asarray([True, True, True], dtype=np.bool_)
    kwargs["candidate_joint_actions"] = np.asarray([1.0, 2.0, -1.0])
    with pytest.raises(OpeningPairContractError, match="integer dtype"):
        build_opening_pair(**kwargs)


def test_route_bound_update_changes_only_bound_q_network() -> None:
    trainer = EEAxisPairwiseTrainer(
        EEAxisPairwiseConfig(
            state_dim=2,
            action_dim=3,
            hidden_layers=(4,),
            activation="tanh",
            learning_rate=1e-3,
            kappa_bits=10.0,
            beta=0.1,
            loss_weights=(1.0, 1.0, 1.0),
        ),
        train_seed=17,
    )
    before = [
        [parameter.detach().clone() for parameter in network.parameters()]
        for network in trainer.q_nets
    ]
    receipt = update_opening_route(
        trainer, build_opening_route_batch([_pair("C3")])
    )

    assert receipt["route"] == "C3"
    changed = [
        any(
            not np.array_equal(
                old.cpu().numpy(), new.detach().cpu().numpy()
            )
            for old, new in zip(before[index], network.parameters(), strict=True)
        )
        for index, network in enumerate(trainer.q_nets)
    ]
    assert changed == [False, False, True]
