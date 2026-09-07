from __future__ import annotations

import hashlib
import math
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_core as C2  # noqa: E402


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def forecast_authority(**changes):
    value = C2.ForecastAuthority(
        schema=C2.FORECAST_AUTHORITY_SCHEMA,
        anchor_sha256=digest("anchor"),
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward-source"),
        live_rng_state_sha256=digest("live-rng"),
        forecast_rng_state_sha256=digest("forecast-rng"),
        forecast_request_sha256=digest("forecast-request"),
        forecast_payload_sha256=digest("forecast-payload"),
        forecast_namespace="c2-v03/unit-fixture",
        fading_mode="disabled",
        generated_preoutcome=True,
        adapter_version="fixture-v1",
    )
    return replace(value, **changes)


def opening_bindings():
    return (
        C2.ActionBinding(3, (50123, 1)),
        C2.ActionBinding(11, (50123, 4)),
    )


def passing_evidence(**changes):
    bindings = opening_bindings()
    value = C2.TemporalForkEvidence(
        authority=forecast_authority(),
        focal_user=7,
        user_count=10,
        reference_action=11,
        candidate_action=3,
        reference_key=(50123, 4),
        candidate_key=(50123, 1),
        opening_action_bindings=bindings,
        opening_action_table_sha256=C2.action_table_sha256(bindings),
        opening_state_sha256=digest("state-0"),
        opening_mask_sha256=digest("mask-0"),
        reference_branch_trace_sha256=digest("reference-branch-trace"),
        candidate_branch_trace_sha256=digest("candidate-branch-trace"),
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
    return replace(value, **changes)


def certified(**changes):
    return C2.certify_temporal_fork(passing_evidence(**changes))


def r2_column(*, focal_user=7, focal_r2=0.0, users=10):
    values = [0.0] * users
    values[focal_user] = focal_r2
    return tuple(values)


def reward_matrix(*, focal_user=7, focal_r2=0.0, users=10):
    r2 = r2_column(focal_user=focal_user, focal_r2=focal_r2, users=users)
    return tuple((1.0, value, -1.0) for value in r2)


def executed_step(certificate, offset, **changes):
    release = offset == certificate.hold_steps
    action = certificate.reference_action if release else certificate.candidate_action
    key = certificate.reference_key if release else certificate.candidate_key
    rewards = reward_matrix(focal_r2=-0.5 if release else 0.0)
    bindings = opening_bindings()
    detached_main_joint = tuple(
        certificate.reference_key
        if user == certificate.focal_user
        else (60000 + user, 0)
        for user in range(certificate.user_count)
    )
    executed_joint = (
        detached_main_joint
        if release
        else tuple(
            certificate.candidate_key
            if user == certificate.focal_user
            else detached_main_joint[user]
            for user in range(certificate.user_count)
        )
    )
    value = C2.ExecutedOptionStep(
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        source_id="C2",
        bundle_id=f"option-bundle-{offset}",
        behavior_probability=0.4 if offset == 0 else 1.0,
        focal_user=certificate.focal_user,
        offset=offset,
        phase="release" if release else "hold",
        action=action,
        physical_key=key,
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
        reward_matrix=rewards,
        reward_matrix_sha256=C2.reward_matrix_sha256(rewards),
        reward_source_sha256=certificate.reward_source_sha256,
        focal_served=True,
        served=(True,) * certificate.user_count,
        state_sha256=digest(f"state-{offset}"),
        state_mask_sha256=digest(f"mask-{offset}"),
        next_state_sha256=digest(f"state-{offset + 1}"),
        next_mask_sha256=digest(f"mask-{offset + 1}"),
        done=False,
    )
    return replace(value, **changes)


def complete_execution(certificate, **last_changes):
    rows = [
        executed_step(certificate, offset)
        for offset in range(certificate.hold_steps + 1)
    ]
    if last_changes:
        rows[-1] = replace(rows[-1], **last_changes)
    return tuple(rows)


def chronology_receipt(certificate, **changes):
    value = SimpleNamespace(
        schema=C2.CHRONOLOGY_RECEIPT_SCHEMA,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        live_rng_before_sha256=digest("live-before"),
        live_rng_after_forecast_sha256=digest("live-before"),
        forecast_rng_sha256=digest("forecast-rng-receipt"),
        forecast_request_sha256=digest("forecast-request-receipt"),
        forecast_payload_sha256=certificate.forecast_payload_sha256,
        forecast_started_ns=10,
        forecast_completed_ns=20,
        live_step_started_ns=21,
        live_step_completed_ns=30,
        forecast_sequence=C2.CHRONOLOGY_SEQUENCE,
        live_rng_unchanged_during_forecast=True,
        claim_ceiling="ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    )
    for field, replacement in changes.items():
        setattr(value, field, replacement)
    return value


def test_passed_fork_exposes_only_main_and_temporal_alternative():
    result = certified()

    assert result.passed
    assert result.support_actions == (11, 3)
    assert result.failures == ()
    assert result.reference_ee_bits_per_j == 10.0
    assert result.ee_surplus_bits == 15.0
    assert result.ee_surplus_floor_bits == pytest.approx(
        C2.MIN_EE_SURPLUS_FRACTION * 100.0
    )
    assert result.hold_r2_margin == 0.5
    assert result.full_r2_margin == 0.5
    assert len(result.option_id) == 64
    assert len(result.evidence_sha256) == 64


def test_epsilon_scale_bits_and_surplus_fail_frozen_robustness_floors():
    tiny = certified(
        reference_useful_bits=1e-12,
        candidate_useful_bits=2e-12,
        reference_energy_j=10.0,
        candidate_energy_j=9.0,
    )
    assert not tiny.passed
    assert C2.ForkFailure.REFERENCE_BITS in tiny.failures

    reference = 100.0
    one_ulp = certified(
        reference_useful_bits=reference,
        candidate_useful_bits=math.nextafter(reference, math.inf),
        reference_energy_j=10.0,
        candidate_energy_j=10.0,
    )
    assert not one_ulp.passed
    assert C2.ForkFailure.EE_SURPLUS in one_ulp.failures

    above = certified(
        reference_useful_bits=reference,
        candidate_useful_bits=(
            reference + 2.0 * C2.MIN_EE_SURPLUS_FRACTION * reference
        ),
        reference_energy_j=10.0,
        candidate_energy_j=10.0,
    )
    assert above.passed


def test_option_identity_changes_when_evidence_or_forecast_lineage_changes():
    baseline = certified()
    changed_metric = certified(candidate_energy_j=8.5)
    changed_payload = C2.certify_temporal_fork(
        passing_evidence(
            authority=forecast_authority(
                forecast_payload_sha256=digest("different-forecast-payload")
            )
        )
    )

    assert changed_metric.evidence_sha256 != baseline.evidence_sha256
    assert changed_metric.option_id != baseline.option_id
    assert changed_payload.evidence_sha256 != baseline.evidence_sha256
    assert changed_payload.option_id != baseline.option_id


@pytest.mark.parametrize(
    ("changes", "failure"),
    [
        ({"branch_structurally_valid": False}, C2.ForkFailure.STRUCTURAL),
        (
            {"nonfocal_policy_aligned": False},
            C2.ForkFailure.NONFOCAL_POLICY_ALIGNMENT,
        ),
        ({"focal_served_all_steps": False}, C2.ForkFailure.FOCAL_SERVICE),
        ({"no_new_nonfocal_outage": False}, C2.ForkFailure.NONFOCAL_OUTAGE),
        ({"release_observed": False}, C2.ForkFailure.RELEASE),
        ({"reference_useful_bits": 0.0}, C2.ForkFailure.REFERENCE_BITS),
        ({"candidate_useful_bits": 99.0}, C2.ForkFailure.USEFUL_BITS),
        (
            {
                "reference_useful_bits": 1e-9,
                "candidate_useful_bits": 1.0,
                "reference_energy_j": 1.0,
                "candidate_energy_j": 100.0,
            },
            C2.ForkFailure.REFERENCE_BITS,
        ),
        (
            {"candidate_useful_bits": 100.0, "candidate_energy_j": 10.0},
            C2.ForkFailure.EE_SURPLUS,
        ),
        ({"forecast_hold_r2_margin": 0.0}, C2.ForkFailure.DIRECT_R2),
        ({"forecast_full_r2_margin": 0.0}, C2.ForkFailure.DIRECT_R2),
    ],
)
def test_semantic_failure_falls_back_to_main_only(changes, failure):
    result = certified(**changes)

    assert not result.passed
    assert failure in result.failures
    assert result.support_actions == (result.reference_action,)


def test_throughput_dominant_ee_gain_does_not_require_lower_energy_or_pulse():
    result = certified(
        activation_or_energy_path=False,
        reference_useful_bits=100.0,
        candidate_useful_bits=200.0,
        reference_energy_j=10.0,
        candidate_energy_j=11.0,
    )

    assert result.passed
    assert result.ee_surplus_bits > result.ee_surplus_floor_bits
    assert C2.ForkFailure.RESOURCE_PATH not in result.failures
    assert C2.ForkFailure.ENERGY_REGRESSION not in result.failures


@pytest.mark.parametrize(
    "authority",
    [
        forecast_authority(
            forecast_rng_state_sha256=forecast_authority().live_rng_state_sha256
        ),
        forecast_authority(forecast_namespace="wrong-domain"),
        forecast_authority(fading_mode="enabled"),
        forecast_authority(generated_preoutcome=False),
    ],
)
def test_forecast_authority_fails_closed_on_leakage(authority):
    with pytest.raises(C2.C2LeakageError):
        C2.certify_temporal_fork(passing_evidence(authority=authority))


def test_ee_overflow_cannot_turn_nan_into_a_pass():
    with pytest.raises(C2.C2ContractError, match="arithmetic"):
        certified(
            reference_useful_bits=1e308,
            candidate_useful_bits=1e308,
            reference_energy_j=1e-320,
            candidate_energy_j=1e-320,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"reference_energy_j": 0.0},
        {"candidate_energy_j": float("nan")},
        {"candidate_useful_bits": -1.0},
        {"forecast_full_r2_margin": float("inf")},
        {"hold_steps": 0},
        {"hold_steps": 4},
        {"candidate_action": 28},
        {"candidate_action": 11},
        {"candidate_key": (50123, 4)},
        {"focal_user": 10},
        {"user_count": 0},
    ],
)
def test_malformed_forecast_fails_closed(changes):
    with pytest.raises(C2.C2ContractError):
        certified(**changes)


def test_opening_action_and_physical_identity_are_bound_by_table_digest():
    bindings = opening_bindings()
    bad_digest = digest("not-the-table")
    with pytest.raises(C2.C2ContractError, match="action-table"):
        certified(opening_action_bindings=bindings, opening_action_table_sha256=bad_digest)

    remapped = (
        C2.ActionBinding(3, (50123, 2)),
        C2.ActionBinding(11, (50123, 4)),
    )
    with pytest.raises(C2.C2ContractError, match="candidate action"):
        certified(
            opening_action_bindings=remapped,
            opening_action_table_sha256=C2.action_table_sha256(remapped),
        )


def test_execution_opening_detached_main_is_the_certified_reference():
    certificate = certified()
    rows = list(complete_execution(certificate))
    detached = list(rows[0].detached_main_joint_physical_actions)
    detached[certificate.focal_user] = certificate.candidate_key
    detached = tuple(detached)
    rows[0] = replace(
        rows[0],
        detached_main_action=certificate.candidate_action,
        detached_main_key=certificate.candidate_key,
        detached_main_joint_physical_actions=detached,
        detached_main_joint_physical_sha256=C2.joint_physical_actions_sha256(
            detached, user_count=certificate.user_count
        ),
    )
    with pytest.raises(C2.C2ContractError, match="certified reference"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_complete_option_builds_private_smdp_and_primitive_main_sequence():
    certificate = certified()
    plan = C2.close_temporal_option(
        certificate,
        complete_execution(certificate),
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert plan.admitted
    assert plan.objective_index == 1
    assert plan.discount_factor == 0.9
    assert plan.complete_hold_and_release
    assert plan.executed_steps == 4
    assert plan.planned_steps == 4
    assert plan.specialist_option_return == pytest.approx(-(0.9**3) * 0.5)
    assert plan.specialist_bootstrap_discount == 0.0
    assert plan.specialist_target_enabled
    assert (
        plan.specialist_target_mode
        == "fixed_horizon_option_return_regression_private_only"
    )
    assert plan.main_sequence_enabled
    assert (
        plan.main_target_mode
        == "canonical_observed_primitive_mean_loss_single_source_unit"
    )
    assert plan.main_source_unit_id == certificate.option_id
    assert plan.observed_bundle_ids == tuple(f"option-bundle-{i}" for i in range(4))
    assert plan.main_bundle_ids == tuple(f"option-bundle-{i}" for i in range(4))
    assert plan.main_behavior_probabilities == (0.4, 1.0, 1.0, 1.0)
    assert plan.opening_state_sha256 == digest("state-0")
    assert plan.bootstrap_state_sha256 == digest("state-4")
    assert plan.bootstrap_mask_sha256 == digest("mask-4")
    assert plan.realised_focal_service_all is True
    assert plan.realised_served_by_step == ((True,) * 10,) * 4
    assert not plan.environment_terminal
    assert plan.disposition == "admit_complete_primitive_sequence_to_q2_only"


def test_terminal_release_has_no_specialist_bootstrap():
    certificate = certified()
    plan = C2.close_temporal_option(
        certificate,
        complete_execution(certificate, done=True),
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert plan.admitted
    assert plan.specialist_bootstrap_discount == 0.0


def test_realised_focal_service_failure_is_retained_as_adverse_training_data():
    certificate = certified()
    rows = list(complete_execution(certificate))
    served = list(rows[1].served)
    served[certificate.focal_user] = False
    rows[1] = replace(rows[1], focal_served=False, served=tuple(served))
    plan = C2.close_temporal_option(
        certificate,
        rows,
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert plan.admitted
    assert plan.specialist_target_enabled
    assert plan.specialist_option_return is not None
    assert plan.main_sequence_enabled
    assert plan.main_bundle_ids == tuple(f"option-bundle-{i}" for i in range(4))
    assert plan.realised_focal_service_all is False
    assert plan.realised_served_by_step[1][certificate.focal_user] is False
    assert plan.disposition == "admit_complete_primitive_sequence_to_q2_only"


def test_only_opening_step_may_have_nonunit_behavior_probability():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[2] = replace(rows[2], behavior_probability=0.5)
    with pytest.raises(C2.C2ContractError, match="must equal one"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)

    rows = list(complete_execution(certificate))
    rows[0] = replace(rows[0], behavior_probability=0.0)
    with pytest.raises(C2.C2ContractError, match=r"\(0,1\]"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_nonterminal_missing_release_is_a_runner_integrity_error():
    certificate = certified()
    partial = list(complete_execution(certificate)[:-1])
    nonzero = reward_matrix(focal_r2=-0.5)
    partial[0] = replace(
        partial[0],
        reward_matrix=nonzero,
        reward_matrix_sha256=C2.reward_matrix_sha256(nonzero),
    )
    with pytest.raises(C2.C2ContractError, match="runner-integrity"):
        C2.close_temporal_option(
            certificate,
            partial,
            discount_factor=0.9,
            chronology_receipt=chronology_receipt(certificate),
        )


def test_real_environment_terminal_retains_observed_prefix_without_padding():
    certificate = certified()
    partial = list(complete_execution(certificate)[:3])
    partial[-1] = replace(partial[-1], done=True)
    plan = C2.close_temporal_option(
        certificate,
        partial,
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert plan.admitted
    assert not plan.complete_hold_and_release
    assert plan.executed_steps == 3
    assert plan.planned_steps == 4
    assert plan.environment_terminal
    assert plan.specialist_target_enabled
    assert plan.specialist_bootstrap_discount == 0.0
    assert plan.main_sequence_enabled
    assert plan.main_bundle_ids == (
        "option-bundle-0",
        "option-bundle-1",
        "option-bundle-2",
    )
    assert plan.main_behavior_probabilities == (0.4, 1.0, 1.0)
    assert plan.disposition == "admit_realised_early_terminal_prefix_to_q2_only"


def test_failed_preoutcome_certificate_can_never_enter_main():
    certificate = certified(forecast_full_r2_margin=0.0)
    plan = C2.close_temporal_option(
        certificate, (), discount_factor=0.9
    )

    assert not plan.admitted
    assert plan.objective_index == 1
    assert not plan.specialist_target_enabled
    assert plan.specialist_option_return is None
    assert not plan.main_sequence_enabled
    assert plan.main_bundle_ids == ()
    assert plan.main_behavior_probabilities == ()
    assert plan.disposition == "zero_dose_preoutcome_certificate_failed"


def test_realised_canonical_r2_magnitude_labels_but_does_not_gate():
    certificate = certified()
    light = C2.close_temporal_option(
        certificate,
        complete_execution(certificate),
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )
    heavy_values = reward_matrix(focal_r2=-1.0)
    heavy_last = replace(
        complete_execution(certificate)[-1],
        reward_matrix=heavy_values,
        reward_matrix_sha256=C2.reward_matrix_sha256(heavy_values),
    )
    heavy_steps = complete_execution(certificate)[:-1] + (heavy_last,)
    heavy = C2.close_temporal_option(
        certificate,
        heavy_steps,
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert light.admitted and heavy.admitted
    assert heavy.specialist_option_return < light.specialist_option_return


def test_complete_option_without_chronology_receipt_is_integrity_error():
    certificate = certified()
    with pytest.raises(C2.C2ContractError, match="chronology receipt"):
        C2.close_temporal_option(
            certificate, complete_execution(certificate), discount_factor=0.9
        )


def test_chronology_receipt_is_hash_bound_and_fail_closed():
    certificate = certified()
    with pytest.raises(C2.C2LeakageError, match="RNG advancement"):
        C2.close_temporal_option(
            certificate,
            complete_execution(certificate),
            discount_factor=0.9,
            chronology_receipt=chronology_receipt(
                certificate,
                live_rng_after_forecast_sha256=digest("advanced-live-rng"),
            ),
        )


def test_arbitrary_negative_value_is_not_canonical_r2():
    certificate = certified()
    values = [list(row) for row in reward_matrix()]
    values[certificate.focal_user][1] = -0.123
    last = replace(
        complete_execution(certificate)[-1],
        reward_matrix=tuple(tuple(row) for row in values),
        reward_matrix_sha256=digest("forged-reward-matrix"),
    )
    with pytest.raises(C2.C2ContractError, match="canonical r2"):
        C2.close_temporal_option(
            certificate,
            complete_execution(certificate)[:-1] + (last,),
            discount_factor=0.9,
        )


def test_release_must_execute_detached_main_action_and_physical_id():
    certificate = certified()
    last = complete_execution(certificate)[-1]
    forged_joint = list(last.executed_joint_physical_actions)
    forged_joint[certificate.focal_user] = certificate.candidate_key
    forged_joint = tuple(forged_joint)
    forged = replace(
        last,
        action=certificate.candidate_action,
        physical_key=certificate.candidate_key,
        executed_joint_physical_actions=forged_joint,
        executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
            forged_joint, user_count=certificate.user_count
        ),
    )
    with pytest.raises(C2.C2ContractError, match="release interval"):
        C2.close_temporal_option(
            certificate,
            complete_execution(certificate)[:-1] + (forged,),
            discount_factor=0.9,
        )


def test_release_may_execute_a_contemporaneous_main_redecision():
    certificate = certified()
    rows = list(complete_execution(certificate))
    release = rows[-1]
    release_action = 5
    release_key = (50123, 8)
    release_bindings = (
        C2.ActionBinding(3, certificate.candidate_key),
        C2.ActionBinding(release_action, release_key),
        C2.ActionBinding(11, certificate.reference_key),
    )
    release_joint = list(release.executed_joint_physical_actions)
    release_joint[certificate.focal_user] = release_key
    release_joint = tuple(release_joint)
    rows[-1] = replace(
        release,
        action=release_action,
        physical_key=release_key,
        detached_main_action=release_action,
        detached_main_key=release_key,
        executed_joint_physical_actions=release_joint,
        executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
            release_joint, user_count=certificate.user_count
        ),
        detached_main_joint_physical_actions=release_joint,
        detached_main_joint_physical_sha256=C2.joint_physical_actions_sha256(
            release_joint, user_count=certificate.user_count
        ),
        action_bindings=release_bindings,
        action_table_sha256=C2.action_table_sha256(release_bindings),
    )

    plan = C2.close_temporal_option(
        certificate,
        rows,
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(certificate),
    )

    assert plan.admitted
    assert plan.main_focal_actions == (3, 3, 3, release_action)


def test_every_hold_interval_keeps_certified_physical_id():
    certificate = certified()
    rows = list(complete_execution(certificate))
    forged_joint = list(rows[1].executed_joint_physical_actions)
    forged_joint[certificate.focal_user] = certificate.reference_key
    forged_joint = tuple(forged_joint)
    rows[1] = replace(
        rows[1],
        action=certificate.reference_action,
        physical_key=certificate.reference_key,
        executed_joint_physical_actions=forged_joint,
        executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
            forged_joint, user_count=certificate.user_count
        ),
    )
    with pytest.raises(C2.C2ContractError, match="hold interval"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_nonfocal_joint_action_must_match_detached_main_branch():
    certificate = certified()
    rows = list(complete_execution(certificate))
    forged_joint = list(rows[1].executed_joint_physical_actions)
    forged_joint[0] = (99999, 9)
    forged_joint = tuple(forged_joint)
    rows[1] = replace(
        rows[1],
        executed_joint_physical_actions=forged_joint,
        executed_joint_physical_sha256=C2.joint_physical_actions_sha256(
            forged_joint, user_count=certificate.user_count
        ),
    )
    with pytest.raises(C2.C2ContractError, match="nonfocal"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_joint_action_hash_and_user_count_are_verified():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(
        rows[1], executed_joint_physical_sha256=digest("wrong-joint-hash")
    )
    with pytest.raises(C2.C2ContractError, match="joint-physical SHA-256"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)

    rows = list(complete_execution(certificate))
    short = rows[1].executed_joint_physical_actions[:-1]
    rows[1] = replace(rows[1], executed_joint_physical_actions=short)
    with pytest.raises(C2.C2ContractError, match="wrong user count"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("option_id", digest("other-option"), "different option"),
        ("anchor_sha256", digest("other-anchor"), "different anchor"),
        ("focal_user", 2, "focal user"),
        ("source_id", "C3", "source"),
        ("reward_source_sha256", digest("other-reward"), "reward implementation"),
    ],
)
def test_transition_identity_cannot_cross_option_or_authority(field, value, message):
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], **{field: value})
    with pytest.raises(C2.C2ContractError, match=message):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_state_chain_must_be_contiguous():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], state_sha256=digest("wrong-state"))
    with pytest.raises(C2.C2ContractError, match="state chain"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_mask_chain_and_opening_anchor_must_be_contiguous():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], state_mask_sha256=digest("wrong-mask"))
    with pytest.raises(C2.C2ContractError, match="mask chain"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)

    rows = list(complete_execution(certificate))
    rows[0] = replace(rows[0], state_sha256=digest("wrong-opening-state"))
    with pytest.raises(C2.C2ContractError, match="opening state"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_bundle_ids_cannot_repeat():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], bundle_id=rows[0].bundle_id)
    with pytest.raises(C2.C2ContractError, match="bundle ID"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_reward_matrix_hash_and_user_count_are_verified():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], reward_matrix_sha256=digest("wrong-reward-hash"))
    with pytest.raises(C2.C2ContractError, match="reward-matrix"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)

    short = reward_matrix(users=9)
    rows = list(complete_execution(certificate))
    rows[1] = replace(
        rows[1],
        reward_matrix=short,
        reward_matrix_sha256=C2.reward_matrix_sha256(short),
    )
    with pytest.raises(C2.C2ContractError, match="user count"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_executed_action_table_hash_and_mapping_are_verified():
    certificate = certified()
    rows = list(complete_execution(certificate))
    rows[1] = replace(rows[1], action_table_sha256=digest("wrong-table"))
    with pytest.raises(C2.C2ContractError, match="action-table"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)

    wrong = (
        C2.ActionBinding(3, (50123, 2)),
        C2.ActionBinding(11, (50123, 4)),
    )
    rows = list(complete_execution(certificate))
    rows[1] = replace(
        rows[1],
        action_bindings=wrong,
        action_table_sha256=C2.action_table_sha256(wrong),
    )
    with pytest.raises(C2.C2ContractError, match="executed action"):
        C2.close_temporal_option(certificate, rows, discount_factor=0.9)


def test_discount_and_length_contracts_are_fail_closed():
    certificate = certified()
    with pytest.raises(C2.C2ContractError):
        C2.close_temporal_option(
            certificate, complete_execution(certificate), discount_factor=math.inf
        )
    extra = complete_execution(certificate) + (
        replace(executed_step(certificate, 3), offset=4, bundle_id="extra"),
    )
    with pytest.raises(C2.C2ContractError, match="past first release"):
        C2.close_temporal_option(certificate, extra, discount_factor=0.9)
