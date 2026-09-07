from __future__ import annotations

import hashlib
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import c2_temporal_fork_core as C2  # noqa: E402
import c2_temporal_fork_forecast_adapter as FORECAST  # noqa: E402


USERS = 3
FOCAL = 1


def digest(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def chronology_receipt(certificate):
    return SimpleNamespace(
        schema=C2.CHRONOLOGY_RECEIPT_SCHEMA,
        option_id=certificate.option_id,
        anchor_sha256=certificate.anchor_sha256,
        live_rng_before_sha256=digest("live-before"),
        live_rng_after_forecast_sha256=digest("live-before"),
        forecast_rng_sha256=digest("forecast-receipt"),
        forecast_request_sha256=digest("request-receipt"),
        forecast_payload_sha256=certificate.forecast_payload_sha256,
        forecast_started_ns=10,
        forecast_completed_ns=20,
        live_step_started_ns=21,
        live_step_completed_ns=30,
        forecast_sequence=C2.CHRONOLOGY_SEQUENCE,
        live_rng_unchanged_during_forecast=True,
        claim_ceiling="ORDER_AND_RNG_NONADVANCEMENT_NOT_EFFICACY",
    )


def source(**changes):
    value = FORECAST.ForecastSourcePayload(
        anchor_payload={"episode": 4, "step": 7, "state": np.array([1.0, 2.0])},
        reference_checkpoint_sha256=digest("checkpoint"),
        environment_source_sha256=digest("environment"),
        reward_source_sha256=digest("reward"),
        live_rng_state={"state": 111, "inc": 7},
        forecast_rng_state={"state": 222, "inc": 9},
        forecast_namespace="c2-v03/authoritative-test",
        adapter_version="authoritative-fixture-v1",
    )
    return replace(value, **changes)


def physical_for(user: int, action: int):
    return (70000 + user, action)


def bindings():
    return tuple(
        (
            C2.ActionBinding(2, physical_for(user, 2)),
            C2.ActionBinding(3, physical_for(user, 3)),
        )
        for user in range(USERS)
    )


def state(branch: str, offset: int):
    branch_shift = 0.0 if offset == 0 or branch == "reference" else 100.0
    return np.asarray(
        [[branch_shift + offset, user, 0.25] for user in range(USERS)],
        dtype=np.float32,
    )


def mask(width=C2.ACTION_DIM):
    result = np.zeros((USERS, width), dtype=bool)
    if width > 3:
        result[:, [2, 3]] = True
    return result


def step(branch: str, offset: int, **changes):
    main_actions = (2, 2, 2)
    main_physical = tuple(physical_for(user, 2) for user in range(USERS))
    candidate_holds = branch == "candidate" and offset < C2.HOLD_STEPS
    executed_actions = list(main_actions)
    executed_physical = list(main_physical)
    if candidate_holds:
        executed_actions[FOCAL] = 3
        executed_physical[FOCAL] = physical_for(FOCAL, 3)
    rewards = [[1.0, 0.0, -1.0] for _ in range(USERS)]
    if branch == "reference":
        rewards[FOCAL][1] = -0.5
    elif offset == C2.HOLD_STEPS:
        rewards[FOCAL][1] = -0.5
    value = FORECAST.ForecastStepPayload(
        offset=offset,
        state_matrix=state(branch, offset),
        mask_matrix=mask(),
        action_bindings_by_user=bindings(),
        detached_main_actions=main_actions,
        detached_main_physical_actions=main_physical,
        executed_actions=tuple(executed_actions),
        executed_physical_actions=tuple(executed_physical),
        reward_matrix=tuple(tuple(row) for row in rewards),
        served=(True, True, True),
        link_rate_bps=(10.0, 10.0, 10.0),
        system_power_w=100.0 if branch == "reference" else 90.0,
        active_physical_ids=((70000, 2), (70001, 2), (70002, 2)),
        next_state_matrix=state(branch, offset + 1),
        next_mask_matrix=mask(),
        done=False,
    )
    return replace(value, **changes)


def traces():
    return (
        tuple(step("reference", offset) for offset in range(4)),
        tuple(step("candidate", offset) for offset in range(4)),
    )


def build(*, source_value=None, reference=None, candidate=None):
    default_reference, default_candidate = traces()
    return FORECAST.build_authoritative_forecast(
        source() if source_value is None else source_value,
        focal_user=FOCAL,
        user_count=USERS,
        pre_active_physical_ids=((70000, 2), (70001, 2), (70002, 2)),
        reference_trace=default_reference if reference is None else reference,
        candidate_trace=default_candidate if candidate is None else candidate,
    )


def test_exact_twin_payload_derives_a_passed_certificate_without_metric_inputs():
    result = build()

    assert result.certificate.passed
    assert result.certificate.support_actions == (2, 3)
    assert result.evidence.hold_steps == 3
    assert result.evidence.forecast_hold_r2_margin == 1.5
    assert result.evidence.forecast_full_r2_margin == 1.5
    assert result.evidence.reference_useful_bits == pytest.approx(3609.6)
    assert result.evidence.candidate_useful_bits == pytest.approx(3609.6)
    assert result.evidence.reference_energy_j == pytest.approx(12032.0)
    assert result.evidence.candidate_energy_j == pytest.approx(10828.8)


def test_explicit_support_expiry_releases_once_and_records_the_first_missing_match():
    reference, candidate = traces()
    no_candidate_mask = mask()
    no_candidate_mask[FOCAL, 3] = False
    no_candidate_bindings = list(bindings())
    no_candidate_bindings[FOCAL] = (C2.ActionBinding(2, physical_for(FOCAL, 2)),)
    changed = []
    for offset, original in enumerate(candidate):
        holding = offset == 0
        row = original
        if not holding:
            row = replace(
                row,
                mask_matrix=no_candidate_mask,
                action_bindings_by_user=tuple(no_candidate_bindings),
                executed_actions=(2, 2, 2),
                executed_physical_actions=tuple(
                    physical_for(user, 2) for user in range(USERS)
                ),
            )
        next_mask = no_candidate_mask if offset < 3 else row.next_mask_matrix
        row = replace(
            row,
            next_mask_matrix=next_mask,
            held_physical_key=physical_for(FOCAL, 3),
            held_key_match_count=1 if holding else 0,
            release_offset=1,
            release_reason="support_expired",
        )
        changed.append(row)

    result = build(reference=reference, candidate=tuple(changed))

    assert result.certificate.passed
    assert result.certificate.release_offset == 1
    assert result.certificate.release_reason == "support_expired"
    assert result.evidence.hold_steps == 1
    assert result.evidence.forecast_hold_r2_margin == pytest.approx(0.5)

    tampered = list(changed)
    tampered[2] = replace(tampered[2], held_key_match_count=1)
    with pytest.raises(C2.C2ContractError, match="held_key_match_count"):
        build(reference=reference, candidate=tuple(tampered))
    assert result.authority.forecast_payload_sha256 == result.forecast_payload_sha256
    assert result.certificate.forecast_payload_sha256 == result.forecast_payload_sha256


def test_changing_one_exact_trace_value_changes_lineage_and_option_identity():
    baseline = build()
    reference, candidate = traces()
    changed_rates = list(candidate[1].link_rate_bps)
    changed_rates[0] += 0.25
    changed = list(candidate)
    changed[1] = replace(changed[1], link_rate_bps=tuple(changed_rates))
    result = build(reference=reference, candidate=tuple(changed))

    assert result.candidate_trace_sha256 != baseline.candidate_trace_sha256
    assert result.forecast_payload_sha256 != baseline.forecast_payload_sha256
    assert result.certificate.evidence_sha256 != baseline.certificate.evidence_sha256
    assert result.certificate.option_id != baseline.certificate.option_id


def test_nonfocal_override_away_from_branch_local_main_fails_alignment():
    reference, candidate = traces()
    changed = list(candidate)
    actions = list(changed[1].executed_actions)
    physical = list(changed[1].executed_physical_actions)
    actions[0] = 3
    physical[0] = physical_for(0, 3)
    changed[1] = replace(
        changed[1],
        executed_actions=tuple(actions),
        executed_physical_actions=tuple(physical),
    )
    result = build(reference=reference, candidate=tuple(changed))

    assert not result.certificate.passed
    assert C2.ForkFailure.NONFOCAL_POLICY_ALIGNMENT in result.certificate.failures


def test_nonfocal_counterfactual_divergence_is_allowed_when_local_main_aligned():
    reference, candidate = traces()
    changed = list(candidate)
    actions = list(changed[1].executed_actions)
    physical = list(changed[1].executed_physical_actions)
    actions[0] = 3
    physical[0] = physical_for(0, 3)
    changed[1] = replace(
        changed[1],
        detached_main_actions=tuple(actions),
        detached_main_physical_actions=tuple(physical),
        executed_actions=tuple(actions),
        executed_physical_actions=tuple(physical),
    )
    result = build(reference=reference, candidate=tuple(changed))

    assert result.certificate.passed
    assert result.evidence.nonfocal_policy_aligned


def test_missing_release_is_derived_as_structural_and_release_failure():
    reference, candidate = traces()
    changed = list(candidate)
    final = changed[-1]
    actions = list(final.executed_actions)
    physical = list(final.executed_physical_actions)
    actions[FOCAL] = 3
    physical[FOCAL] = physical_for(FOCAL, 3)
    changed[-1] = replace(
        final,
        executed_actions=tuple(actions),
        executed_physical_actions=tuple(physical),
    )
    result = build(reference=reference, candidate=tuple(changed))

    assert not result.certificate.passed
    assert C2.ForkFailure.STRUCTURAL in result.certificate.failures
    assert C2.ForkFailure.RELEASE in result.certificate.failures


def test_opening_twin_mismatch_and_rng_alias_fail_as_leakage():
    reference, candidate = traces()
    changed = list(candidate)
    wrong = np.array(changed[0].state_matrix, copy=True)
    wrong[0, 0] += 1.0
    changed[0] = replace(changed[0], state_matrix=wrong)
    with pytest.raises(C2.C2LeakageError, match="opening state"):
        build(reference=reference, candidate=tuple(changed))

    with pytest.raises(C2.C2LeakageError, match="aliases"):
        build(
            source_value=source(forecast_rng_state={"state": 111, "inc": 7})
        )


def test_action_width_and_trace_chain_fail_closed():
    reference, candidate = traces()
    broken_width = list(candidate)
    broken_width[0] = replace(
        broken_width[0], mask_matrix=mask(27), next_mask_matrix=mask(27)
    )
    with pytest.raises(C2.C2ContractError, match="Boolean"):
        build(reference=reference, candidate=tuple(broken_width))

    broken_chain = list(candidate)
    wrong_state = np.array(broken_chain[1].state_matrix, copy=True)
    wrong_state[0, 0] += 1.0
    broken_chain[1] = replace(broken_chain[1], state_matrix=wrong_state)
    with pytest.raises(C2.C2ContractError, match="chain"):
        build(reference=reference, candidate=tuple(broken_chain))


def test_canonical_payload_hashes_numpy_contents_not_object_identity():
    left = {"array": np.asarray([[1.0, 2.0]], dtype=np.float32)}
    right = {"array": np.asarray([[1.0, 2.0]], dtype=np.float32)}
    changed = {"array": np.asarray([[1.0, 2.5]], dtype=np.float32)}

    assert FORECAST.canonical_payload_sha256(left) == FORECAST.canonical_payload_sha256(right)
    assert FORECAST.canonical_payload_sha256(left) != FORECAST.canonical_payload_sha256(changed)


def test_actual_committed_arrays_build_a_complete_hash_bound_closure():
    forecast = build()
    _, candidate = traces()
    closure = FORECAST.close_committed_option(
        forecast.certificate,
        bundle_ids=tuple(f"actual-{offset}" for offset in range(4)),
        committed_steps=candidate,
        behavior_probabilities=(0.25, 1.0, 1.0, 1.0),
        reward_source_sha256=forecast.certificate.reward_source_sha256,
        discount_factor=0.9,
        chronology_receipt=chronology_receipt(forecast.certificate),
    )

    assert len(closure.receipts) == 4
    assert closure.plan.admitted
    assert closure.plan.specialist_target_enabled
    assert closure.plan.main_sequence_enabled
    assert closure.plan.main_source_unit_id == forecast.certificate.option_id
    assert len(closure.plan.chronology_receipt_sha256) == 64
    assert closure.receipts[0].state_sha256 == forecast.certificate.opening_state_sha256
    assert closure.receipts[0].state_mask_sha256 == forecast.certificate.opening_mask_sha256


def test_actual_committed_reward_source_and_opening_state_are_recomputed():
    forecast = build()
    _, candidate = traces()
    with pytest.raises(C2.C2ContractError, match="reward source"):
        FORECAST.build_executed_option_step(
            forecast.certificate,
            bundle_id="actual-0",
            committed_step=candidate[0],
            behavior_probability=0.25,
            reward_source_sha256=digest("wrong-reward-source"),
        )

    changed = list(candidate)
    wrong = np.array(changed[0].state_matrix, copy=True)
    wrong[FOCAL, 0] += 5.0
    changed[0] = replace(changed[0], state_matrix=wrong)
    with pytest.raises(C2.C2ContractError, match="opening state"):
        FORECAST.close_committed_option(
            forecast.certificate,
            bundle_ids=tuple(f"actual-{offset}" for offset in range(4)),
            committed_steps=tuple(changed),
            behavior_probabilities=(0.25, 1.0, 1.0, 1.0),
            reward_source_sha256=forecast.certificate.reward_source_sha256,
            discount_factor=0.9,
        )
