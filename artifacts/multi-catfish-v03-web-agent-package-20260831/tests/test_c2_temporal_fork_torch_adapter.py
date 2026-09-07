from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
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

import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_learning_adapter as L  # noqa: E402
import c2_temporal_fork_torch_adapter as T  # noqa: E402
from smc_er_core import AtomicBundle, ObjectiveSpecialist  # noqa: E402
from mcrl.algorithms.modqn import MODQNTrainer  # noqa: E402
from mcrl.runtime.trainer_spec import TrainerConfig  # noqa: E402


STATE_DIM = 4 * 28
ACTION_DIM = 28


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _mask(*actions: int, width: int = ACTION_DIM) -> np.ndarray:
    value = np.zeros(width, dtype=np.bool_)
    for action in actions:
        value[action] = True
    return value


def _chronology_receipt(certificate):
    return SimpleNamespace(
        schema=C2.CHRONOLOGY_RECEIPT_SCHEMA,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        live_rng_before_sha256=digest("torch-live-before"),
        live_rng_after_forecast_sha256=digest("torch-live-before"),
        forecast_rng_sha256=digest("torch-forecast-rng"),
        forecast_request_sha256=digest("torch-forecast-request"),
        forecast_payload_sha256=certificate.forecast_payload_sha256,
        forecast_started_ns=10,
        forecast_completed_ns=20,
        live_step_started_ns=21,
        live_step_completed_ns=30,
        forecast_sequence=C2.CHRONOLOGY_SEQUENCE,
        live_rng_unchanged_during_forecast=True,
        claim_ceiling="ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    )


def _admitted_items(*, terminal: bool = False):
    anchor = digest("torch-anchor")
    reward_source = digest("torch-reward-source")
    opening_state = np.full(STATE_DIM, 0.125, dtype=np.float32)
    opening_mask = _mask(3, 11)
    bindings = (
        C2.ActionBinding(3, (50123, 1)),
        C2.ActionBinding(11, (50123, 4)),
    )
    authority = C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=anchor,
        reference_checkpoint_sha256=digest("torch-checkpoint"),
        environment_source_sha256=digest("torch-environment"),
        reward_source_sha256=reward_source,
        live_rng_state_sha256=digest("torch-live-rng"),
        forecast_rng_state_sha256=digest("torch-detached-rng"),
        forecast_request_sha256=digest("torch-request"),
        forecast_payload_sha256=digest("torch-payload"),
        forecast_namespace="c2-v03/torch-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="torch-fixture-v2",
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
            reference_branch_trace_sha256=digest("torch-reference-trace"),
            candidate_branch_trace_sha256=digest("torch-candidate-trace"),
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
    steps: list[C2.ExecutedOptionStep] = []
    bundles: list[AtomicBundle] = []
    for offset in range(L.EXPECTED_DURATION):
        state = np.full((1, STATE_DIM), offset + 0.125, dtype=np.float32)
        next_state = np.full((1, STATE_DIM), offset + 1.125, dtype=np.float32)
        masks = np.asarray([_mask(3, 11)], dtype=np.bool_)
        next_masks = (
            np.zeros_like(masks)
            if terminal and offset == L.EXPECTED_DURATION - 1
            else masks.copy()
        )
        action = 3 if offset < C2.HOLD_STEPS else 11
        physical_key = (50123, 1) if offset < C2.HOLD_STEPS else (50123, 4)
        r2 = (0.0, -0.5, -1.0, 0.0)[offset]
        rewards = np.asarray([[0.25, r2, -0.75]], dtype=np.float64)
        state_hash = L.array_sha256(state[0])
        state_mask_hash = L.array_sha256(masks[0])
        next_state_hash = L.array_sha256(next_state[0])
        next_mask_hash = L.array_sha256(next_masks[0])
        reward_hash = C2.reward_matrix_sha256(rewards.tolist())
        r2_hash = C2.r2_column_sha256((r2,))
        provenance = {
            "option_id": certificate.option_id,
            "anchor_sha256": anchor,
            "evidence_sha256": certificate.evidence_sha256,
            "selection_receipt_sha256": digest("selection-receipt"),
            "offset": offset,
            "phase": "hold" if offset < C2.HOLD_STEPS else "release",
            "state_sha256": state_hash,
            "state_mask_sha256": state_mask_hash,
            "next_state_sha256": next_state_hash,
            "next_mask_sha256": next_mask_hash,
            "reward_matrix_sha256": reward_hash,
            "r2_column_sha256": r2_hash,
            "reward_source_sha256": reward_source,
            "focal_served": True,
            "served": (True,),
        }
        executed_joint = (physical_key,)
        detached_main_joint = ((50123, 4),)
        steps.append(
            C2.ExecutedOptionStep(
                option_id=certificate.option_id,
                anchor_sha256=anchor,
                source_id="C2",
                bundle_id=f"torch-c2-bundle-{offset}",
                behavior_probability=0.5 if offset == 0 else 1.0,
                focal_user=0,
                offset=offset,
                phase="hold" if offset < C2.HOLD_STEPS else "release",
                action=action,
                physical_key=physical_key,
                detached_main_action=11,
                detached_main_key=(50123, 4),
                executed_joint_physical_actions=executed_joint,
                executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
                    executed_joint, user_count=1
                ),
                detached_main_joint_physical_actions=detached_main_joint,
                detached_main_joint_physical_sha256=C2.joint_physical_actions_sha256(
                    detached_main_joint, user_count=1
                ),
                action_bindings=bindings,
                action_table_sha256=C2.action_table_sha256(bindings),
                reward_matrix=tuple(tuple(row) for row in rewards.tolist()),
                reward_matrix_sha256=reward_hash,
                reward_source_sha256=reward_source,
                focal_served=True,
                served=(True,),
                state_sha256=state_hash,
                state_mask_sha256=state_mask_hash,
                next_state_sha256=next_state_hash,
                next_mask_sha256=next_mask_hash,
                done=bool(terminal and offset == L.EXPECTED_DURATION - 1),
            )
        )
        bundles.append(
            AtomicBundle(
                bundle_id=f"torch-c2-bundle-{offset}",
                source_id="C2",
                source_policy_version=1,
                block_id=0,
                step_index=offset,
                states=state,
                actions=np.asarray([action], dtype=np.int64),
                rewards=rewards,
                next_states=next_state,
                masks=masks,
                next_masks=next_masks,
                done=bool(terminal and offset == L.EXPECTED_DURATION - 1),
                focal_user=0,
                behavior_probabilities=np.asarray(
                    [0.5 if offset == 0 else 1.0]
                ),
                provenance=provenance,
            )
        )
    plan = C2.close_temporal_option(
        certificate,
        steps,
        discount_factor=0.9,
        chronology_receipt=_chronology_receipt(certificate),
    )
    sequence = L.C2PrimitiveSequence.from_plan(plan, certificate, bundles)
    transition = L.C2SMDPTransition.from_plan(
        plan,
        certificate,
        opening_state=opening_state,
        opening_mask=opening_mask,
        bootstrap_state=np.full(STATE_DIM, 4.125, dtype=np.float32),
        bootstrap_mask=next_masks[0],
        reward_matrices=tuple(bundle.rewards.tolist() for bundle in bundles),
        discount_factor=0.9,
        terminal=terminal,
        selection_receipt_sha256=digest("selection-receipt"),
    )
    return certificate, plan, tuple(steps), tuple(bundles), transition, sequence


def _sequence() -> L.C2PrimitiveSequence:
    return _admitted_items()[-1]


def _transition(*, terminal: bool = False) -> L.C2SMDPTransition:
    return _admitted_items(terminal=terminal)[-2]


def _specialist(
    *, terminal: bool = False, calibration_scale: float | None = None
) -> ObjectiveSpecialist:
    config = TrainerConfig(
        hidden_layers=(4,),
        learning_rate=0.001,
        discount_factor=0.9,
        batch_size=1,
        episodes=1,
        reward_calibration_enabled=calibration_scale is not None,
        reward_calibration_scales=(1.0, calibration_scale or 1.0, 1.0),
    )
    specialist = ObjectiveSpecialist(
        objective_index=1,
        state_dim=STATE_DIM,
        action_dim=ACTION_DIM,
        config=config,
        seed=909 if not terminal else 910,
    )
    # Deliberately make the target network extreme: fixed-window Q2F regression
    # must ignore it while the online network still receives a real step.
    with torch.no_grad():
        for parameter in specialist.target.parameters():
            parameter.zero_()
        specialist.target.net[-1].bias[11] = 2.0
    return specialist


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
            reward_calibration_scales=(1.0, calibration_scale or 1.0, 1.0),
        ),
        train_seed=77,
        env_seed=78,
        mobility_seed=79,
    )


def _populate_replay(main: MODQNTrainer, count: int = 2) -> None:
    mask = np.ones(ACTION_DIM, dtype=np.bool_)
    for index in range(count):
        state = np.full(main.state_dim, 0.1 + index, dtype=np.float32)
        next_state = np.full(main.state_dim, 0.2 + index, dtype=np.float32)
        main.replay.push(
            state,
            3,
            np.asarray([0.2, -0.5, -1.0], dtype=np.float32),
            next_state,
            mask,
            mask,
            False,
        )


def _same_network(left: MODQNTrainer, right: MODQNTrainer, objective: int) -> bool:
    left_state = left.q_nets[objective].state_dict()
    right_state = right.q_nets[objective].state_dict()
    return all(torch_equal(left_state[key], right_state[key]) for key in left_state)


def torch_equal(left: object, right: object) -> bool:
    return bool(torch.equal(left, right))


def test_q2f_fixed_window_regression_ignores_post_release_target_network():
    specialist = _specialist()
    transition = _transition()
    receipt = T.update_q2f_smdp(specialist, transition)
    expected = transition.option_return
    assert receipt.duration == 4
    assert receipt.bootstrap_discount == 0.0
    assert receipt.target == pytest.approx(expected)
    assert receipt.optimizer_steps == 1
    assert specialist.updates == 1


def test_q2f_terminal_transition_ignores_all_bootstrap_q_values():
    specialist = _specialist(terminal=True)
    transition = _transition(terminal=True)
    receipt = T.update_q2f_smdp(specialist, transition)
    assert receipt.bootstrap_discount == 0.0
    assert receipt.target == pytest.approx(transition.option_return)


def test_q2f_calibrates_the_observed_option_return_exactly_once():
    specialist = _specialist(calibration_scale=2.0)
    transition = _transition()
    receipt = T.update_q2f_smdp(specialist, transition)
    expected = transition.option_return / 2.0
    assert receipt.reward_calibration_scale == 2.0
    assert receipt.calibrated_option_return == pytest.approx(
        transition.option_return / 2.0
    )
    assert receipt.target == pytest.approx(expected)


def test_q2f_optimizer_failure_restores_network_and_update_counter(monkeypatch):
    specialist = _specialist()
    transition = _transition()
    before = {
        key: value.detach().cpu().clone()
        for key, value in specialist.online.state_dict().items()
    }

    def mutate_then_fail():
        with torch.no_grad():
            next(specialist.online.parameters()).add_(100.0)
        raise RuntimeError("synthetic specialist step failure")

    monkeypatch.setattr(specialist.optimizer, "step", mutate_then_fail)
    with pytest.raises(RuntimeError, match="synthetic specialist step failure"):
        T.update_q2f_smdp(specialist, transition)
    assert specialist.updates == 0
    assert all(
        torch_equal(specialist.online.state_dict()[key], value)
        for key, value in before.items()
    )


def test_q2f_actual_payload_hash_mismatch_fails_before_optimizer_step():
    specialist = _specialist()
    transition = _transition()
    changed = transition.opening_state.copy()
    changed[0] += 1.0
    with pytest.raises(L.LearningContractError, match="sequence_sha256"):
        replace(transition, opening_state=changed)
    assert specialist.updates == 0


def test_mean_primitive_loss_is_one_fourth_and_ledger_is_checkpointable():
    sequence = _sequence()
    assert L.mean_primitive_loss((1.0, 2.0, 3.0, 4.0)) == pytest.approx(2.5)
    ledger = T.C2OptionLedger()
    pending = ledger.preflight(sequence)
    assert pending.bundle_ids == sequence.constituent_bundle_ids
    assert len(ledger) == 0
    committed = ledger.commit(sequence)
    assert committed == pending
    assert len(ledger) == 1
    restored = T.C2OptionLedger()
    restored.load_state_dict(ledger.state_dict())
    assert len(restored) == 1
    with pytest.raises(T.TorchAdapterContractError, match="already consumed"):
        restored.preflight(sequence)


def test_option_ledger_rejects_pre_v03b_or_unlabelled_replay_state():
    sequence = _sequence()
    ledger = T.C2OptionLedger()
    ledger.commit(sequence)
    snapshot = ledger.state_dict()

    old_format = copy.deepcopy(snapshot)
    old_format["format_version"] = 1
    with pytest.raises(ValueError, match="unsupported C2 option ledger format"):
        T.C2OptionLedger().load_state_dict(old_format)

    missing_policy = copy.deepcopy(snapshot)
    del missing_policy["c2_policy_version"]
    with pytest.raises(ValueError, match="policy version"):
        T.C2OptionLedger().load_state_dict(missing_policy)


def test_main_c2_blend_keeps_q1_q3_bitwise_baseline_and_changes_q2_once():
    sequence = _sequence()
    baseline = _main()
    routed = _main()
    _populate_replay(baseline)
    _populate_replay(routed)
    baseline.update()
    receipt = T.update_main_with_c2_sequence_once(
        routed, sequence, beta=0.5, option_ledger=T.C2OptionLedger()
    )
    assert receipt.updated and receipt.committed
    assert receipt.effective_beta == pytest.approx(0.5)
    assert receipt.primitive_count == 4
    assert receipt.optimizer_steps_per_objective == (1, 1, 1)
    assert _same_network(baseline, routed, 0)
    assert _same_network(baseline, routed, 2)
    assert not _same_network(baseline, routed, 1)


def test_main_c2_calibrates_each_raw_primitive_reward_exactly_once():
    main = _main(calibration_scale=2.0)
    _populate_replay(main)
    with torch.no_grad():
        for parameter in main.q_nets[1].parameters():
            parameter.zero_()
        for parameter in main.target_nets[1].parameters():
            parameter.zero_()
    receipt = T.update_main_with_c2_sequence_once(
        main,
        _sequence(),
        beta=0.5,
        option_ledger=T.C2OptionLedger(),
    )
    # Raw r2 values (0, -0.5, -1, 0) become (0, -0.25, -0.5, 0).
    expected_mean = (0.0**2 + 0.25**2 + 0.5**2 + 0.0**2) / 4.0
    assert receipt.primitive_loss_mean == pytest.approx(expected_mean)


def test_main_c2_warmup_does_not_sample_rng_or_burn_option():
    main = _main()
    _populate_replay(main, count=1)
    sequence = _sequence()
    ledger = T.C2OptionLedger()
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)
    before = tuple(
        {
            key: value.detach().cpu().clone()
            for key, value in network.state_dict().items()
        }
        for network in main.q_nets
    )
    receipt = T.update_main_with_c2_sequence_once(main, sequence, 0.5, ledger)
    assert receipt.warmup and not receipt.updated and not receipt.committed
    assert len(ledger) == 0
    assert main._train_rng.bit_generator.state == rng_before
    for network, snapshot in zip(main.q_nets, before, strict=True):
        assert all(torch_equal(network.state_dict()[key], value) for key, value in snapshot.items())


def test_main_c2_failure_before_commit_rolls_back_and_does_not_burn_option():
    class FailingLedger(T.C2OptionLedger):
        def commit(self, sequence):  # type: ignore[no-untyped-def]
            super().commit(sequence)
            raise RuntimeError("synthetic commit failure")

    main = _main()
    _populate_replay(main)
    sequence = _sequence()
    ledger = FailingLedger()
    before = tuple(
        {
            key: value.detach().cpu().clone()
            for key, value in network.state_dict().items()
        }
        for network in main.q_nets
    )
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        T.update_main_with_c2_sequence_once(main, sequence, 0.5, ledger)
    assert len(ledger) == 0
    assert main._train_rng.bit_generator.state == rng_before
    for network, snapshot in zip(main.q_nets, before, strict=True):
        assert all(torch_equal(network.state_dict()[key], value) for key, value in snapshot.items())


def test_main_c2_single_beta_and_duplicate_option_are_fail_closed():
    main = _main()
    _populate_replay(main, count=4)
    sequence = _sequence()
    ledger = T.C2OptionLedger()
    receipt = T.update_main_with_c2_sequence_once(main, sequence, 0.25, ledger)
    assert receipt.effective_beta == pytest.approx(0.25)
    assert receipt.constituent_bundle_ids == sequence.constituent_bundle_ids
    assert receipt.blended_q2_loss == pytest.approx(
        0.75 * receipt.main_losses[1] + 0.25 * receipt.primitive_loss_mean
    )
    assert receipt.dose_borrowing is False
    rng_before = copy.deepcopy(main._train_rng.bit_generator.state)
    with pytest.raises(T.TorchAdapterContractError, match="already consumed"):
        T.update_main_with_c2_sequence_once(main, sequence, 0.25, ledger)
    assert main._train_rng.bit_generator.state == rng_before


def test_optimizer_boundaries_refuse_a_tampered_admission_flag():
    sequence = copy.copy(_sequence())
    object.__setattr__(sequence, "admitted", False)
    with pytest.raises(L.LearningContractError, match="not admitted"):
        T.update_main_with_c2_sequence_once(
            _main(), sequence, 0.25, T.C2OptionLedger()
        )

    transition = copy.copy(_transition())
    object.__setattr__(transition, "admitted", False)
    with pytest.raises(L.LearningContractError, match="not admitted"):
        T.update_q2f_smdp(_specialist(), transition)
