from __future__ import annotations

import hashlib
import sys
from dataclasses import fields, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SMC_DIR = HERE.parent / "smc-er-short-ep"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SMC_DIR))

import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_forecast_adapter as Forecast  # noqa: E402
import c2_temporal_fork_learning_adapter as L  # noqa: E402
from smc_er_core import AtomicBundle  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def authority() -> C2.ForecastAuthority:
    return C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=digest("anchor"),
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward-source"),
        live_rng_state_sha256=digest("live-rng"),
        forecast_rng_state_sha256=digest("forecast-rng"),
        forecast_request_sha256=digest("request"),
        forecast_payload_sha256=digest("payload"),
        forecast_namespace="c2-v03/learning-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="learning-fixture-v1",
    )


def _opening_mask() -> np.ndarray:
    value = np.zeros(C2.ACTION_DIM, dtype=np.bool_)
    value[3] = True
    value[11] = True
    return value


def _state(offset: int) -> np.ndarray:
    return np.asarray(
        [offset + 0.1, offset + 0.2, offset + 0.3], dtype=np.float32
    )


def _full_mask() -> np.ndarray:
    value = np.zeros(C2.ACTION_DIM, dtype=np.bool_)
    value[3] = True
    value[11] = True
    return value


def _chronology_receipt(certificate):
    return SimpleNamespace(
        schema=C2.CHRONOLOGY_RECEIPT_SCHEMA,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        live_rng_before_sha256=digest("learning-live-before"),
        live_rng_after_forecast_sha256=digest("learning-live-before"),
        forecast_rng_sha256=digest("learning-forecast-rng"),
        forecast_request_sha256=digest("learning-forecast-request"),
        forecast_payload_sha256=certificate.forecast_payload_sha256,
        forecast_started_ns=10,
        forecast_completed_ns=20,
        live_step_started_ns=21,
        live_step_completed_ns=30,
        forecast_sequence=C2.CHRONOLOGY_SEQUENCE,
        live_rng_unchanged_during_forecast=True,
        claim_ceiling="ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    )


def _evidence() -> tuple[C2.TemporalForkEvidence, np.ndarray, np.ndarray]:
    opening_state = _state(0)
    opening_mask = _opening_mask()
    bindings = (
        C2.ActionBinding(3, (50123, 1)),
        C2.ActionBinding(11, (50123, 4)),
    )
    evidence = C2.TemporalForkEvidence(
        authority=authority(),
        focal_user=0,
        user_count=2,
        reference_action=11,
        candidate_action=3,
        reference_key=(50123, 4),
        candidate_key=(50123, 1),
        opening_action_bindings=bindings,
        opening_action_table_sha256=C2.action_table_sha256(bindings),
        opening_state_sha256=L.array_sha256(opening_state),
        opening_mask_sha256=L.array_sha256(opening_mask),
        reference_branch_trace_sha256=digest("reference-trace"),
        candidate_branch_trace_sha256=digest("candidate-trace"),
        hold_steps=3,
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
    return evidence, opening_state, opening_mask


def _steps_and_bundles(
    certificate: C2.TemporalForkCertificate,
    *,
    terminal: bool = False,
    release_redecision: bool = False,
) -> tuple[tuple[C2.ExecutedOptionStep, ...], tuple[AtomicBundle, ...]]:
    steps: list[C2.ExecutedOptionStep] = []
    bundles: list[AtomicBundle] = []
    bindings = (
        C2.ActionBinding(3, (50123, 1)),
        C2.ActionBinding(11, (50123, 4)),
    )
    action_table_hash = C2.action_table_sha256(bindings)
    for offset in range(C2.HOLD_STEPS + 1):
        release = offset == C2.HOLD_STEPS
        action = (
            5
            if release and release_redecision
            else certificate.reference_action
            if release
            else certificate.candidate_action
        )
        physical_key = (
            (50123, 8)
            if release and release_redecision
            else certificate.reference_key
            if release
            else certificate.candidate_key
        )
        state = _state(offset)
        next_state = _state(offset + 1)
        mask = _full_mask()
        if release and release_redecision:
            mask[5] = True
        next_mask = _full_mask()
        if release_redecision and offset >= C2.HOLD_STEPS - 1:
            next_mask[5] = True
        reward_matrix = ((1.0, -0.5 if release else 0.0, -1.0), (0.5, 0.0, -0.5))
        detached_main_joint = (
            physical_key if release else certificate.reference_key,
            (60000, 0),
        )
        executed_joint = (
            detached_main_joint
            if release
            else (certificate.candidate_key, (60000, 0))
        )
        state_hash = L.array_sha256(state)
        mask_hash = L.array_sha256(mask)
        next_state_hash = L.array_sha256(next_state)
        next_mask_hash = L.array_sha256(next_mask)
        reward_hash = C2.reward_matrix_sha256(reward_matrix)
        r2_hash = C2.r2_column_sha256(tuple(row[1] for row in reward_matrix))
        behavior_probability = 0.5 if offset == 0 else 1.0
        step_bindings = (
            bindings
            if not (release and release_redecision)
            else (
                C2.ActionBinding(3, certificate.candidate_key),
                C2.ActionBinding(5, physical_key),
                C2.ActionBinding(11, certificate.reference_key),
            )
        )
        step_fields = {field.name for field in fields(C2.ExecutedOptionStep)}
        step_kwargs = dict(
            option_id=certificate.option_id,
            anchor_sha256=certificate.anchor_sha256,
            source_id="C2",
            bundle_id=f"learning-bundle-{offset}",
            focal_user=certificate.focal_user,
            offset=offset,
            phase="release" if release else "hold",
            action=action,
            physical_key=physical_key,
            detached_main_action=(action if release else certificate.reference_action),
            detached_main_key=(physical_key if release else certificate.reference_key),
            executed_joint_physical_actions=executed_joint,
            executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
                executed_joint, user_count=certificate.user_count
            ),
            detached_main_joint_physical_actions=detached_main_joint,
            detached_main_joint_physical_sha256=C2.joint_physical_actions_sha256(
                detached_main_joint, user_count=certificate.user_count
            ),
            action_bindings=step_bindings,
            action_table_sha256=C2.action_table_sha256(step_bindings),
            reward_matrix=reward_matrix,
            reward_matrix_sha256=reward_hash,
            reward_source_sha256=certificate.reward_source_sha256,
            state_sha256=state_hash,
            state_mask_sha256=mask_hash,
            next_state_sha256=next_state_hash,
            next_mask_sha256=next_mask_hash,
            done=bool(terminal and release),
        )
        if "behavior_probability" in step_fields:
            step_kwargs["behavior_probability"] = behavior_probability
        if "focal_served" in step_fields:
            step_kwargs["focal_served"] = True
        if "served" in step_fields:
            step_kwargs["served"] = (True,) * certificate.user_count
        step = C2.ExecutedOptionStep(**step_kwargs)
        steps.append(step)
        actions = np.asarray(
            [action, certificate.reference_action], dtype=np.int64
        )
        states = np.asarray([state, _state(10 + offset)], dtype=np.float32)
        next_states = np.asarray(
            [next_state, _state(11 + offset)], dtype=np.float32
        )
        masks = np.asarray([mask, mask], dtype=np.bool_)
        next_masks = np.asarray([next_mask, next_mask], dtype=np.bool_)
        provenance = {
            "option_id": certificate.option_id,
            "anchor_sha256": certificate.anchor_sha256,
            "evidence_sha256": certificate.evidence_sha256,
            "selection_receipt_sha256": digest("selection-receipt"),
            "offset": offset,
            "environment_step_index": 100 + offset,
            "phase": "release" if release else "hold",
            "state_sha256": state_hash,
            "state_mask_sha256": mask_hash,
            "next_state_sha256": next_state_hash,
            "next_mask_sha256": next_mask_hash,
            "reward_matrix_sha256": reward_hash,
            "r2_column_sha256": r2_hash,
            "reward_source_sha256": certificate.reward_source_sha256,
            "focal_served": True,
            "served": (True,) * certificate.user_count,
        }
        bundles.append(
            AtomicBundle(
                bundle_id=step.bundle_id,
                source_id="C2",
                source_policy_version=1,
                block_id=0,
                step_index=100 + offset,
                states=states,
                actions=actions,
                rewards=np.asarray(reward_matrix, dtype=np.float64),
                next_states=next_states,
                masks=masks,
                next_masks=next_masks,
                done=bool(terminal and release),
                focal_user=certificate.focal_user,
                behavior_probabilities=np.asarray(
                    [behavior_probability, behavior_probability]
                ),
                provenance=provenance,
            )
        )
    return tuple(steps), tuple(bundles)


def fixture(*, terminal: bool = False):
    evidence, opening_state, opening_mask = _evidence()
    certificate = C2.certify_temporal_fork(evidence)
    steps, bundles = _steps_and_bundles(certificate, terminal=terminal)
    plan = C2.close_temporal_option(
        certificate,
        steps,
        discount_factor=0.9,
        chronology_receipt=_chronology_receipt(certificate),
    )
    reward_matrices = tuple(bundle.rewards.tolist() for bundle in bundles)
    transition = L.C2SMDPTransition.from_plan(
        plan,
        certificate,
        opening_state=opening_state,
        opening_mask=opening_mask,
        bootstrap_state=_state(4),
        bootstrap_mask=_full_mask(),
        reward_matrices=reward_matrices,
        discount_factor=0.9,
        terminal=terminal,
        selection_receipt_sha256=digest("selection-receipt"),
    )
    sequence = L.C2PrimitiveSequence.from_plan(
        plan, certificate, bundles
    )
    return certificate, plan, steps, bundles, transition, sequence


def test_fixed_window_target_uses_observed_return_without_off_support_bootstrap():
    _, plan, _, _, transition, _ = fixture()
    assert transition.duration == 4
    assert transition.option_return == pytest.approx(-(0.9**3) * 0.5)
    assert transition.bootstrap_discount == 0.0
    q_next = np.zeros(C2.ACTION_DIM, dtype=np.float64)
    q_next[11] = 10.0
    q_next[3] = 4.0
    expected = -(0.9**3) * 0.5
    assert L.c2_smdp_target(transition, q_next) == pytest.approx(expected)
    calibrated = (-(0.9**3) * 0.5) / 2.0
    assert L.c2_smdp_target(
        transition,
        q_next,
        reward_calibration_enabled=True,
        reward_calibration_scale=2.0,
    ) == pytest.approx(calibrated)
    assert plan.specialist_option_return == transition.option_return
    assert L.array_sha256(_state(0)) == Forecast.canonical_payload_sha256(
        tuple(_state(0).tolist())
    )


def test_configured_gamma_must_match_the_admitted_plan():
    certificate, plan, _, bundles, _, _ = fixture()
    with pytest.raises(L.LearningContractError, match="discount_factor"):
        L.C2SMDPTransition.from_plan(
            plan,
            certificate,
            opening_state=_state(0),
            opening_mask=_opening_mask(),
            bootstrap_state=_state(4),
            bootstrap_mask=_full_mask(),
            reward_matrices=tuple(bundle.rewards.tolist() for bundle in bundles),
            discount_factor=0.8,
            terminal=False,
            selection_receipt_sha256=digest("selection-receipt"),
        )


def test_terminal_option_has_zero_bootstrap_and_ignores_next_q():
    _, plan, _, _, transition, _ = fixture(terminal=True)
    assert plan.specialist_bootstrap_discount == 0.0
    assert transition.bootstrap_discount == 0.0
    q_next = np.full(C2.ACTION_DIM, 1e6, dtype=np.float64)
    assert L.c2_smdp_target(transition, q_next) == pytest.approx(
        transition.option_return
    )


@pytest.mark.parametrize("field", ["opening_state", "bootstrap_state", "bootstrap_mask"])
def test_actual_state_or_mask_hash_mismatch_fails_closed(field):
    certificate, plan, _, bundles, _, _ = fixture()
    kwargs = {
        "opening_state": _state(0),
        "opening_mask": _opening_mask(),
        "bootstrap_state": _state(4),
        "bootstrap_mask": _full_mask(),
    }
    value = kwargs[field].copy()
    if value.dtype == np.bool_:
        value[0] = ~value[0]
    else:
        value[0] += 1.0
    kwargs[field] = value
    with pytest.raises(L.LearningContractError, match="hash"):
        L.C2SMDPTransition.from_plan(
            plan,
            certificate,
            **kwargs,
            reward_matrices=tuple(bundle.rewards.tolist() for bundle in bundles),
            discount_factor=0.9,
            terminal=False,
            selection_receipt_sha256=digest("selection-receipt"),
        )


def test_incomplete_or_failed_plan_cannot_create_learning_items():
    certificate, plan, steps, bundles, _, _ = fixture()
    with pytest.raises(C2.C2ContractError, match="runner-integrity"):
        C2.close_temporal_option(
            certificate,
            steps[:-1],
            discount_factor=0.9,
            chronology_receipt=_chronology_receipt(certificate),
        )
    failed_certificate = C2.certify_temporal_fork(
        replace(
            next(iter([_evidence()[0]])),
            forecast_full_r2_margin=0.0,
        )
    )
    failed_plan = C2.close_temporal_option(
        failed_certificate, (), discount_factor=0.9
    )
    with pytest.raises(L.LearningContractError, match="admitted"):
        L.C2PrimitiveSequence.from_plan(
            failed_plan, failed_certificate, ()
        )


def test_sequence_preserves_hash_bound_identity_and_rejects_missing_constituent():
    certificate, plan, _, bundles, _, sequence = fixture()
    assert len(sequence.transitions) == 4
    assert sequence.constituent_bundle_ids == plan.main_bundle_ids
    assert sequence.source_unit_id == certificate.option_id
    assert sequence.target_objective == 1
    assert sequence.admitted is True
    assert sequence.chronology_receipt_sha256 == plan.chronology_receipt_sha256
    assert L.assert_admission_bound(sequence) == sequence.admission_proof
    with pytest.raises(L.LearningContractError, match="constituent bundle IDs"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, bundles[:-1])

    changed = list(bundles)
    provenance = dict(changed[1].provenance)
    provenance["evidence_sha256"] = digest("wrong-evidence")
    changed[1] = replace(changed[1], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="evidence"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)


def test_learning_items_reject_missing_or_false_admission():
    _, _, _, _, transition, sequence = fixture()
    with pytest.raises(L.LearningContractError, match="not admitted"):
        replace(sequence, admitted=False)
    with pytest.raises(L.LearningContractError, match="lacks an admission proof"):
        replace(transition, admission_proof=object())


def test_contemporaneous_release_redecision_survives_learning_seam():
    evidence, _, _ = _evidence()
    certificate = C2.certify_temporal_fork(evidence)
    steps, bundles = _steps_and_bundles(
        certificate, release_redecision=True
    )
    plan = C2.close_temporal_option(
        certificate,
        steps,
        discount_factor=0.9,
        chronology_receipt=_chronology_receipt(certificate),
    )

    sequence = L.C2PrimitiveSequence.from_plan(plan, certificate, bundles)

    assert plan.admitted
    assert plan.main_focal_actions == (3, 3, 3, 5)
    assert int(sequence.transitions[-1].actions[certificate.focal_user]) == 5


def test_sequence_rejects_chain_and_reward_hash_mismatch():
    certificate, plan, _, bundles, _, _ = fixture()
    changed = list(bundles)
    provenance = dict(changed[1].provenance)
    provenance["state_sha256"] = digest("wrong-state")
    changed[1] = replace(changed[1], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="state_sha256"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)


def test_learning_seam_rejects_stale_or_unlabelled_v03b_replay_rows():
    certificate, plan, _, bundles, _, _ = fixture()

    stale = list(bundles)
    stale_provenance = dict(stale[0].provenance)
    stale_provenance.update(
        {
            "c2_policy_version": "C2_V0.3A_FIXED_HOLD",
            "release_offset": 3,
            "release_reason": "horizon",
        }
    )
    stale[0] = replace(stale[0], provenance=stale_provenance)
    with pytest.raises(L.LearningContractError, match="active V0.3B policy"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, stale)

    unlabelled = list(bundles)
    unlabelled_provenance = dict(unlabelled[0].provenance)
    unlabelled_provenance.update(
        {
            "release_offset": 3,
            "release_reason": "horizon",
            "held_physical_key": certificate.candidate_key,
            "held_key_match_count": 1,
        }
    )
    unlabelled[0] = replace(unlabelled[0], provenance=unlabelled_provenance)
    with pytest.raises(L.LearningContractError, match="lacks active policy version"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, unlabelled)


def test_sequence_rechecks_behavior_probability_when_plan_exposes_it():
    certificate, plan, _, bundles, _, _ = fixture()
    changed = list(bundles)
    provenance = dict(changed[1].provenance)
    provenance["behavior_probability"] = 0.5
    changed[1] = replace(
        changed[1],
        behavior_probabilities=np.asarray([0.5, 0.5]),
        provenance=provenance,
    )
    with pytest.raises(L.LearningContractError, match="behavior probability"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)

    changed = list(bundles)
    provenance = dict(changed[2].provenance)
    provenance["reward_matrix_sha256"] = digest("wrong-reward")
    changed[2] = replace(changed[2], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="reward"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)


def test_sequence_rejects_served_or_reward_source_drift_from_sealed_plan():
    certificate, plan, _, bundles, _, _ = fixture()
    changed = list(bundles)
    provenance = dict(changed[1].provenance)
    provenance["served"] = (False, False)
    provenance["focal_served"] = False
    changed[1] = replace(changed[1], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="served vector"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)

    changed = list(bundles)
    provenance = dict(changed[2].provenance)
    provenance["reward_source_sha256"] = digest("wrong-reward-source")
    changed[2] = replace(changed[2], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="reward source"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)

    changed = list(bundles)
    provenance = dict(changed[3].provenance)
    del provenance["served"]
    changed[3] = replace(changed[3], provenance=provenance)
    with pytest.raises(L.LearningContractError, match="lacks served"):
        L.C2PrimitiveSequence.from_plan(plan, certificate, changed)


def test_four_primitive_losses_are_one_mean_source_unit_not_a_sum():
    _, _, _, _, _, sequence = fixture()
    losses = (1.0, 2.0, 3.0, 4.0)
    assert L.mean_primitive_loss(losses) == pytest.approx(2.5)
    assert L.mean_primitive_loss(losses) != pytest.approx(sum(losses))
    receipt = L.blend_main_q2_single_beta(
        sequence, main_loss=10.0, primitive_losses=losses, beta=0.25
    )
    assert receipt.primitive_count == 4
    assert receipt.unit_weight == 1.0
    assert receipt.effective_beta == pytest.approx(0.25)
    assert receipt.primitive_loss_mean == pytest.approx(2.5)
    assert receipt.blended_loss == pytest.approx(8.125)
    assert receipt.constituent_bundle_ids == sequence.constituent_bundle_ids
    assert receipt.sequence_sha256 == sequence.sequence_sha256
    assert receipt.dose_borrowing is False


def test_q1_q2_q3_mapping_is_diagonal_and_c2_only_targets_q2():
    _, _, _, _, _, sequence = fixture()
    assert L.ROLE_TO_OBJECTIVE == {"C1": 0, "C2": 1, "C3": 2}
    assert L.target_objective_for_source("C1") == 0
    assert L.target_objective_for_source("C2") == 1
    assert L.target_objective_for_source("C3") == 2
    receipt = L.blend_main_q2_single_beta(
        sequence, main_loss=1.0, primitive_losses=(1.0, 1.0, 1.0, 1.0), beta=0.2
    )
    assert receipt.target_objective == 1
    assert receipt.q1_q3_donor_targets == ()
    with pytest.raises(L.LearningContractError, match="C2"):
        L.target_objective_for_source("Main")
