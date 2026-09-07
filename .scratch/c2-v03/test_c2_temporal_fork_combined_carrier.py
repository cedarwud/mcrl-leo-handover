"""Focused contract tests for the one-sample C1/C2/C3 Main carrier."""

from __future__ import annotations

import copy
from dataclasses import fields
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
import torch


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))
sys.path.insert(0, str(HERE.parents[1] / "src"))

import c2_temporal_fork_combined_carrier as C  # noqa: E402
import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_learning_adapter as L  # noqa: E402
import c2_temporal_fork_torch_adapter as T  # noqa: E402
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402
from smc_er_core import AtomicBundle, ConsumedBundleLedger  # noqa: E402


STATE_DIM = 4 * 28
ACTION_DIM = 28


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _MainEnv:
    num_beams_total = ACTION_DIM

    class _Config:
        num_users = 1

    config = _Config()


def _main(*, calibration_scale: float | None = None) -> MODQNTrainer:
    return MODQNTrainer(
        _MainEnv(),
        TrainerConfig(
            hidden_layers=(4,),
            learning_rate=0.001,
            discount_factor=0.9,
            batch_size=2,
            replay_capacity=16,
            episodes=1,
            reward_calibration_enabled=calibration_scale is not None,
            reward_calibration_scales=(
                calibration_scale or 1.0,
                calibration_scale or 1.0,
                calibration_scale or 1.0,
            ),
        ),
        train_seed=77,
        env_seed=78,
        mobility_seed=79,
    )


def _populate_replay(main: MODQNTrainer, count: int = 2) -> None:
    mask = np.ones(ACTION_DIM, dtype=np.bool_)
    for index in range(count):
        main.replay.push(
            np.full(STATE_DIM, 0.1 + index, dtype=np.float32),
            3,
            np.asarray((0.2, -0.5, -1.0), dtype=np.float32),
            np.full(STATE_DIM, 0.2 + index, dtype=np.float32),
            mask,
            mask,
            False,
        )


def _mask() -> np.ndarray:
    value = np.zeros(ACTION_DIM, dtype=np.bool_)
    value[[3, 11]] = True
    return value


def _bundle(
    source: str,
    bundle_id: str,
    *,
    focal: int | None = None,
    block_id: int = 0,
    policy_version: int = 1,
) -> AtomicBundle:
    states = np.full((1, STATE_DIM), 0.25, dtype=np.float32)
    next_states = np.full((1, STATE_DIM), 0.5, dtype=np.float32)
    masks = np.asarray([_mask()], dtype=np.bool_)
    rewards = np.asarray([[0.4, -0.5, -0.75]], dtype=np.float64)
    return AtomicBundle(
        bundle_id=bundle_id,
        source_id=source,
        source_policy_version=policy_version,
        block_id=block_id,
        step_index=0,
        states=states,
        actions=np.asarray([3], dtype=np.int64),
        rewards=rewards,
        next_states=next_states,
        masks=masks,
        next_masks=masks.copy(),
        done=False,
        focal_user=focal,
        behavior_probabilities=np.asarray([0.5], dtype=np.float64),
    )


def _admitted_c2_fixture(
    *, block_id: int = 0, policy_version: int = 1
) -> tuple[object, C2.TemporalForkCertificate, tuple[AtomicBundle, ...]]:
    """Build a real admitted plan and sequence through the public C2 seam."""

    anchor = digest("combined-anchor")
    reward_source = digest("combined-reward-source")
    opening_state = np.full(STATE_DIM, 0.125, dtype=np.float32)
    opening_mask = _mask()
    bindings = (
        C2.ActionBinding(3, (50123, 1)),
        C2.ActionBinding(11, (50123, 4)),
    )
    authority = C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=anchor,
        reference_checkpoint_sha256=digest("combined-checkpoint"),
        environment_source_sha256=digest("combined-environment"),
        reward_source_sha256=reward_source,
        live_rng_state_sha256=digest("combined-live-rng"),
        forecast_rng_state_sha256=digest("combined-forecast-rng"),
        forecast_request_sha256=digest("combined-request"),
        forecast_payload_sha256=digest("combined-payload"),
        forecast_namespace="c2-v03/combined-carrier-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="combined-carrier-fixture-v1",
    )
    certificate = C2.certify_temporal_fork(
        C2.TemporalForkEvidence(
            authority=authority,
            focal_user=0,
            user_count=1,
            reference_action=11,
            candidate_action=3,
            reference_key=(50123, 4),
            candidate_key=(50123, 1),
            opening_action_bindings=bindings,
            opening_action_table_sha256=C2.action_table_sha256(bindings),
            opening_state_sha256=L.array_sha256(opening_state),
            opening_mask_sha256=L.array_sha256(opening_mask),
            reference_branch_trace_sha256=digest("combined-reference-trace"),
            candidate_branch_trace_sha256=digest("combined-candidate-trace"),
            hold_steps=C2.HOLD_STEPS,
            release_observed=True,
            branch_structurally_valid=True,
            nonfocal_policy_aligned=True,
            focal_served_all_steps=True,
            no_new_nonfocal_outage=True,
            activation_or_energy_path=True,
            reference_useful_bits=100.0,
            candidate_useful_bits=105.0,
            reference_energy_j=10.0,
            candidate_energy_j=9.0,
            forecast_hold_r2_margin=0.5,
            forecast_full_r2_margin=0.5,
        )
    )
    chronology = SimpleNamespace(
        schema=C2.CHRONOLOGY_RECEIPT_SCHEMA,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        live_rng_before_sha256=digest("combined-live-before"),
        live_rng_after_forecast_sha256=digest("combined-live-before"),
        forecast_rng_sha256=digest("combined-forecast-state"),
        forecast_request_sha256=digest("combined-forecast-request"),
        forecast_payload_sha256=certificate.forecast_payload_sha256,
        forecast_started_ns=10,
        forecast_completed_ns=20,
        live_step_started_ns=21,
        live_step_completed_ns=30,
        forecast_sequence=C2.CHRONOLOGY_SEQUENCE,
        live_rng_unchanged_during_forecast=True,
        claim_ceiling="ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    )
    steps: list[C2.ExecutedOptionStep] = []
    bundles: list[AtomicBundle] = []
    rewards_by_offset = (0.0, -0.5, -1.0, 0.0)
    step_fields = {field.name for field in fields(C2.ExecutedOptionStep)}
    for offset, r2 in enumerate(rewards_by_offset):
        release = offset == C2.HOLD_STEPS
        action = certificate.reference_action if release else certificate.candidate_action
        physical_key = certificate.reference_key if release else certificate.candidate_key
        state = np.full(STATE_DIM, offset + 0.125, dtype=np.float32)
        next_state = np.full(STATE_DIM, offset + 1.125, dtype=np.float32)
        mask = _mask()
        reward_matrix = ((0.25, r2, -0.75),)
        state_hash = L.array_sha256(state)
        mask_hash = L.array_sha256(mask)
        next_state_hash = L.array_sha256(next_state)
        next_mask_hash = mask_hash
        reward_hash = C2.reward_matrix_sha256(reward_matrix)
        r2_hash = C2.r2_column_sha256((r2,))
        executed_joint = (physical_key,)
        detached_main_joint = (certificate.reference_key,)
        behavior_probability = 0.5 if offset == 0 else 1.0
        step_kwargs = dict(
            option_id=certificate.option_id,
            anchor_sha256=certificate.anchor_sha256,
            source_id="C2",
            bundle_id=f"combined-c2-bundle-{offset}",
            focal_user=certificate.focal_user,
            offset=offset,
            phase="release" if release else "hold",
            action=action,
            physical_key=physical_key,
            detached_main_action=certificate.reference_action,
            detached_main_key=certificate.reference_key,
            executed_joint_physical_actions=executed_joint,
            executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
                executed_joint, user_count=certificate.user_count
            ),
            detached_main_joint_physical_actions=detached_main_joint,
            detached_main_joint_physical_sha256=C2.joint_physical_actions_sha256(
                detached_main_joint, user_count=certificate.user_count
            ),
            action_bindings=bindings,
            action_table_sha256=C2.action_table_sha256(bindings),
            reward_matrix=reward_matrix,
            reward_matrix_sha256=reward_hash,
            reward_source_sha256=certificate.reward_source_sha256,
            state_sha256=state_hash,
            state_mask_sha256=mask_hash,
            next_state_sha256=next_state_hash,
            next_mask_sha256=next_mask_hash,
            focal_served=True,
            served=(True,),
            done=False,
        )
        if "behavior_probability" in step_fields:
            step_kwargs["behavior_probability"] = behavior_probability
        steps.append(C2.ExecutedOptionStep(**step_kwargs))
        bundles.append(
            AtomicBundle(
                bundle_id=step_kwargs["bundle_id"],
                source_id="C2",
                source_policy_version=policy_version,
                block_id=block_id,
                step_index=offset,
                states=state.reshape(1, -1),
                actions=np.asarray([action], dtype=np.int64),
                rewards=np.asarray(reward_matrix, dtype=np.float64),
                next_states=next_state.reshape(1, -1),
                masks=mask.reshape(1, -1),
                next_masks=mask.reshape(1, -1).copy(),
                done=False,
                focal_user=0,
                behavior_probabilities=np.asarray([behavior_probability], dtype=np.float64),
                provenance={
                    "option_id": certificate.option_id,
                    "anchor_sha256": certificate.anchor_sha256,
                    "evidence_sha256": certificate.evidence_sha256,
                    "selection_receipt_sha256": digest("selection-receipt"),
                    "offset": offset,
                    "phase": "release" if release else "hold",
                    "state_sha256": state_hash,
                    "state_mask_sha256": mask_hash,
                    "next_state_sha256": next_state_hash,
                    "next_mask_sha256": next_mask_hash,
                    "reward_matrix_sha256": reward_hash,
                    "r2_column_sha256": r2_hash,
                    "reward_source_sha256": certificate.reward_source_sha256,
                    "behavior_probability": behavior_probability,
                    "focal_served": True,
                    "served": (True,),
                },
            )
        )
    plan = C2.close_temporal_option(
        certificate, steps, discount_factor=0.9, chronology_receipt=chronology
    )
    assert plan.admitted
    sequence = L.C2PrimitiveSequence.from_plan(plan, certificate, bundles)
    return plan, certificate, tuple(bundles), sequence


def _c2_sequence(
    *, block_id: int = 0, policy_version: int = 1
) -> L.C2PrimitiveSequence:
    return _admitted_c2_fixture(
        block_id=block_id, policy_version=policy_version
    )[-1]


def _same_network(left: MODQNTrainer, right: MODQNTrainer, objective: int) -> bool:
    return all(
        torch.equal(left.q_nets[objective].state_dict()[key], value)
        for key, value in right.q_nets[objective].state_dict().items()
    )


def _prepare(main: MODQNTrainer, *, all_sources: bool = True):
    _populate_replay(main)
    c1 = _bundle("C1", "combined-c1") if all_sources else None
    c2 = _c2_sequence() if all_sources else None
    c3 = _bundle("C3", "combined-c3", focal=0) if all_sources else None
    consumed = ConsumedBundleLedger() if all_sources else None
    c2_ledger = T.C2OptionLedger() if all_sources else None
    return c1, c2, c3, consumed, c2_ledger


def test_all_three_share_one_sample_and_keep_diagonal_head_isolation(monkeypatch):
    all_main = _main()
    c1, c2, c3, consumed, c2_ledger = _prepare(all_main)
    calls = {"sample": 0}
    optimizer_steps = [0, 0, 0]
    original_sample = all_main.replay.sample

    def counted_sample(count, rng):
        calls["sample"] += 1
        return original_sample(count, rng)

    all_main.replay.sample = counted_sample
    for objective, optimizer in enumerate(all_main.optimizers):
        original_step = optimizer.step

        def counted_step(*args, _objective=objective, _original=original_step, **kwargs):
            optimizer_steps[_objective] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(optimizer, "step", counted_step)
    receipt = C.update_main_with_combined_carrier(
        all_main,
        c1_bundle=c1,
        c2_sequence=c2,
        c3_bundle=c3,
        beta=0.5,
        consumed_ledger=consumed,
        c2_option_ledger=c2_ledger,
        consumer_block_id=0,
    )
    assert receipt.active_sources == ("C1", "C2", "C3")
    assert receipt.canonical_sample_count == 1
    assert calls["sample"] == 1
    assert optimizer_steps == [1, 1, 1]
    assert receipt.optimizer_steps_per_objective == (1, 1, 1)
    assert len(consumed) == 2
    assert len(c2_ledger) == 1
    assert receipt.source_block_id == {"C1": 0, "C2": 0, "C3": 0}
    assert receipt.source_policy_version == {"C1": 1, "C2": 1, "C3": 1}
    assert receipt.consumer_block_id == 0
    assert receipt.source_age_blocks == {"C1": 0, "C2": 0, "C3": 0}

    c1_main = _main()
    c1_only, _c2, _c3, c1_ledger, _c2ledger = _prepare(c1_main)
    C.update_main_with_combined_carrier(
        c1_main,
        c1_bundle=c1_only,
        beta=0.5,
        consumed_ledger=c1_ledger,
        consumer_block_id=0,
    )
    c3_main = _main()
    _c1, _c2, c3_only, c3_ledger, _c2ledger = _prepare(c3_main)
    C.update_main_with_combined_carrier(
        c3_main,
        c3_bundle=c3_only,
        beta=0.5,
        consumed_ledger=c3_ledger,
        consumer_block_id=0,
    )
    # Adding C2/C3 cannot perturb Q1; adding C1/C2 cannot perturb Q3.
    assert _same_network(all_main, c1_main, 0)
    assert _same_network(all_main, c3_main, 2)
    assert receipt.effective_beta == {"C1": 0.5, "C2": 0.5, "C3": 0.5}


def test_absent_sources_delegate_to_exact_baseline_and_rng_schedule():
    baseline = _main()
    routed = _main()
    _populate_replay(baseline)
    _populate_replay(routed)
    expected = baseline.update()
    receipt = C.update_main_with_combined_carrier(routed)
    assert receipt.mode == "exact_baseline_delegate"
    assert receipt.canonical_sample_count == 1
    assert receipt.optimizer_steps_per_objective == (1, 1, 1)
    assert tuple(receipt.blended_losses) == pytest.approx(expected)
    assert all(_same_network(baseline, routed, objective) for objective in range(3))
    assert baseline._train_rng.bit_generator.state == routed._train_rng.bit_generator.state


def test_c2_mean_and_raw_calibration_are_applied_once():
    main = _main(calibration_scale=2.0)
    _populate_replay(main)
    with torch.no_grad():
        for parameter in main.q_nets[1].parameters():
            parameter.zero_()
        for parameter in main.target_nets[1].parameters():
            parameter.zero_()
    receipt = C.update_main_with_combined_carrier(
        main,
        c2_sequence=_c2_sequence(),
        beta=0.5,
        c2_option_ledger=T.C2OptionLedger(),
        consumer_block_id=0,
    )
    expected_mean = (0.0**2 + 0.25**2 + 0.5**2 + 0.0**2) / 4.0
    assert receipt.c2_primitive_count == 4
    assert receipt.donor_losses["C2"] == pytest.approx(expected_mean)
    assert receipt.blended_losses[1] == pytest.approx(
        0.5 * receipt.canonical_main_losses[1] + 0.5 * expected_mean
    )


def test_warmup_does_not_sample_or_burn_any_ledger():
    main = _main()
    c1, c2, c3, consumed, c2_ledger = _prepare(main)
    # Replace the two replay rows with one, below the configured batch size.
    main.replay._buf.pop()
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)
    receipt = C.update_main_with_combined_carrier(
        main,
        c1_bundle=c1,
        c2_sequence=c2,
        c3_bundle=c3,
        consumed_ledger=consumed,
        c2_option_ledger=c2_ledger,
        consumer_block_id=0,
    )
    assert receipt.warmup and not receipt.updated
    assert receipt.canonical_sample_count == 0
    assert len(consumed) == 0 and len(c2_ledger) == 0
    assert main._train_rng.bit_generator.state == rng_before


def test_optimizer_failure_rolls_back_networks_rng_and_both_ledgers(monkeypatch):
    main = _main()
    c1, c2, c3, consumed, c2_ledger = _prepare(main)
    before = [
        {key: value.detach().cpu().clone() for key, value in net.state_dict().items()}
        for net in main.q_nets
    ]
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)

    def mutate_then_fail():
        with torch.no_grad():
            next(main.q_nets[1].parameters()).add_(100.0)
        raise RuntimeError("combined synthetic optimizer failure")

    monkeypatch.setattr(main.optimizers[1], "step", mutate_then_fail)
    with pytest.raises(RuntimeError, match="combined synthetic optimizer failure"):
        C.update_main_with_combined_carrier(
            main,
            c1_bundle=c1,
            c2_sequence=c2,
            c3_bundle=c3,
            consumed_ledger=consumed,
            c2_option_ledger=c2_ledger,
            consumer_block_id=0,
        )
    assert len(consumed) == 0 and len(c2_ledger) == 0
    assert main._train_rng.bit_generator.state == rng_before
    for network, snapshot in zip(main.q_nets, before, strict=True):
        assert all(torch.equal(network.state_dict()[key], value) for key, value in snapshot.items())


def test_duplicate_cross_source_consumption_is_rejected_before_sampling():
    main = _main()
    c1, c2, c3, consumed, c2_ledger = _prepare(main)
    first = C.update_main_with_combined_carrier(
        main,
        c1_bundle=c1,
        c2_sequence=c2,
        c3_bundle=c3,
        consumed_ledger=consumed,
        c2_option_ledger=c2_ledger,
        consumer_block_id=0,
    )
    assert first.committed_c2_option_id == c2.option_id
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)
    with pytest.raises(Exception, match="already consumed"):
        C.update_main_with_combined_carrier(
            main,
            c2_sequence=c2,
            c2_option_ledger=c2_ledger,
            consumer_block_id=0,
        )
    assert main._train_rng.bit_generator.state == rng_before

    duplicate_main = _main()
    _populate_replay(duplicate_main)
    with pytest.raises(Exception, match="already consumed"):
        C.update_main_with_combined_carrier(
            duplicate_main,
            c1_bundle=c1,
            consumed_ledger=consumed,
            consumer_block_id=0,
        )


def test_focal_and_source_authority_is_not_optional():
    main = _main()
    _populate_replay(main)
    c1_with_focal = _bundle("C1", "bad-c1", focal=0)
    with pytest.raises(C.CombinedCarrierContractError, match="joint source"):
        C.update_main_with_combined_carrier(
            main,
            c1_bundle=c1_with_focal,
            consumed_ledger=ConsumedBundleLedger(),
            consumer_block_id=0,
        )
    main = _main()
    _populate_replay(main)
    c3_without_focal = _bundle("C3", "bad-c3", focal=None)
    with pytest.raises(C.CombinedCarrierContractError, match="requires focal_user"):
        C.update_main_with_combined_carrier(
            main,
            c3_bundle=c3_without_focal,
            consumed_ledger=ConsumedBundleLedger(),
            consumer_block_id=0,
        )


def test_active_source_age_is_explicit_and_fails_closed_before_sampling():
    main = _main()
    _populate_replay(main)
    c2 = _c2_sequence(block_id=2, policy_version=7)
    ledger = T.C2OptionLedger()
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)

    with pytest.raises(C.CombinedCarrierContractError, match="consumer_block_id"):
        C.update_main_with_combined_carrier(
            main,
            c2_sequence=c2,
            c2_option_ledger=ledger,
        )
    with pytest.raises(C.CombinedCarrierContractError, match="future consumer block"):
        C.update_main_with_combined_carrier(
            main,
            c2_sequence=c2,
            c2_option_ledger=ledger,
            consumer_block_id=1,
        )
    with pytest.raises(C.CombinedCarrierContractError, match="exceeds frozen maximum"):
        C.update_main_with_combined_carrier(
            main,
            c2_sequence=c2,
            c2_option_ledger=ledger,
            consumer_block_id=3,
        )
    assert main._train_rng.bit_generator.state == rng_before
    assert len(ledger) == 0

    receipt = C.update_main_with_combined_carrier(
        main,
        c2_sequence=c2,
        c2_option_ledger=ledger,
        consumer_block_id=2,
    )
    assert receipt.source_block_id == {"C2": 2}
    assert receipt.source_policy_version == {"C2": 7}
    assert receipt.source_age_blocks == {"C2": 0}
