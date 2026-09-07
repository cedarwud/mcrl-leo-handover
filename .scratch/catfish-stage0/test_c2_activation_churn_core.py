"""Focused deterministic fixtures for C2 activation-churn V3 spec items 2--11."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).with_name("c2_activation_churn_core.py")
spec = importlib.util.spec_from_file_location("c2_activation_churn_core", MODULE_PATH)
c2 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = c2
spec.loader.exec_module(c2)


INCUMBENT = (100, 1)
RELOCATION = (200, 2)
OTHER = (300, 3)


def _hold(physical_id=INCUMBENT, **changes):
    return c2.HoldInterval(
        physical_id=physical_id,
        recurrence_power_w=0.5,
        canonical_link_ceiling_w=1.0,
        **changes,
    )


def _sequence(declared_id, holds, **changes):
    values = dict(
        incumbent_id=INCUMBENT,
        declared_id=declared_id,
        hold_intervals=holds,
        release_action=OTHER,
        release_from_main=True,
        full_release_window=True,
    )
    values.update(changes)
    return c2.validate_candidate_sequence(**values)


def test_physical_id_remapping_survives_reordering_and_duplicates_fail_closed():
    assert c2.remap_physical_id([INCUMBENT, RELOCATION, OTHER], RELOCATION) == 1
    assert c2.remap_physical_id([OTHER, INCUMBENT, RELOCATION], RELOCATION) == 2
    with pytest.raises(ValueError, match="duplicate"):
        c2.unique_physical_id_map([INCUMBENT, RELOCATION, INCUMBENT])
    with pytest.raises(ValueError, match="not uniquely remappable"):
        c2.remap_physical_id([INCUMBENT, OTHER], RELOCATION)


def test_incumbent_hold_and_one_relocation_plus_hold_are_the_only_grammars():
    stay = _sequence(INCUMBENT, [_hold()] * 3)
    relocate = _sequence(RELOCATION, [_hold(RELOCATION)] * 3)
    assert stay.passed and stay.form is c2.CandidateForm.INCUMBENT_HOLD
    assert relocate.passed and relocate.form is c2.CandidateForm.RELOCATION_HOLD


def test_candidate_sequence_rejects_truthy_nonboolean_control_flags():
    with pytest.raises(ValueError, match="Boolean"):
        _sequence(INCUMBENT, [_hold()] * 3, release_from_main=1)
    with pytest.raises(ValueError, match="Boolean"):
        _sequence(
            INCUMBENT,
            [_hold(), _hold(hidden_fallback="false"), _hold()],
        )


@pytest.mark.parametrize(
    ("holds", "changes", "reason"),
    [
        ([_hold(RELOCATION), _hold(OTHER), _hold(RELOCATION)], {}, "second_relocation_or_redraw"),
        ([_hold(RELOCATION), _hold(INCUMBENT), _hold(RELOCATION)], {}, "second_relocation_or_redraw"),
        ([_hold(RELOCATION), _hold(RELOCATION, hidden_fallback=True), _hold(RELOCATION)], {}, "hidden_fallback"),
        ([_hold(RELOCATION), _hold(RELOCATION, expired=True), _hold(RELOCATION)], {}, "early_expiry"),
        ([_hold(RELOCATION)] * 2, {}, "hold_window_incomplete"),
        ([_hold(RELOCATION)] * 3, {"full_release_window": False}, "release_window_incomplete"),
        ([_hold(RELOCATION)] * 3, {"release_from_main": False}, "release_window_incomplete"),
    ],
)
def test_redraw_fallback_expiry_and_short_windows_are_rejected(holds, changes, reason):
    result = _sequence(RELOCATION, holds, **changes)
    assert not result.passed
    assert result.reason == reason


def test_first_failed_hold_offset_precedes_later_release_failure():
    result = _sequence(
        RELOCATION,
        [_hold(RELOCATION), _hold(RELOCATION, hidden_fallback=True), _hold(RELOCATION)],
        full_release_window=False,
    )
    assert not result.passed
    assert result.failed_offset == 1
    assert result.reason == "hidden_fallback"


def test_one_changed_nonfocal_physical_action_rejects_even_if_shape_is_equal():
    reference = [[INCUMBENT, None], [RELOCATION, OTHER], [OTHER, None], [INCUMBENT, OTHER]]
    same = [list(row) for row in reference]
    changed = [list(row) for row in reference]
    changed[1][0] = OTHER
    assert c2.nonfocal_physical_identity(reference, same)
    assert not c2.nonfocal_physical_identity(reference, changed)


def _active(sequence, resource=INCUMBENT):
    return [[resource] if present else [] for present in sequence]


def test_exact_beam_and_satellite_off_on_off_pulse_is_identified_separately():
    result = c2.activation_pulses(
        _active([False, True, True, False, False]),
        _active([False, False, False, False, False]),
    )
    assert result.beam_pulses == frozenset({INCUMBENT})
    assert result.satellite_pulses == frozenset({INCUMBENT[0]})


@pytest.mark.parametrize(
    ("reference", "candidate"),
    [
        ([True, True, False, False, False], [False] * 5),       # pre-active
        ([False, True, True, True, True], [False] * 5),        # active after release
        ([False, True, False, True, False], [False] * 5),      # gap/reactivation
        ([False, True, False, False, False], [False, True, False, False, False]),
    ],
)
def test_pre_active_post_release_gapped_reactivated_or_shared_beam_is_not_a_pulse(
    reference, candidate
):
    result = c2.activation_pulses(_active(reference), _active(candidate))
    assert not result.beam_pulses
    assert not result.satellite_pulses


def test_satellite_shared_by_a_different_candidate_beam_blocks_satellite_only():
    reference = _active([False, True, False, False, False], (100, 1))
    candidate = _active([False, True, False, False, False], (100, 9))
    result = c2.activation_pulses(reference, candidate)
    assert result.beam_pulses == frozenset({(100, 1)})
    assert not result.satellite_pulses


def test_mechanism_passes_by_exact_pulse_or_strictly_lower_complete_energy_only():
    pulse = c2.ActivationPulseDecision(frozenset({INCUMBENT}), frozenset())
    no_pulse = c2.ActivationPulseDecision(frozenset(), frozenset())
    assert c2.evaluate_activation_energy_mechanism(
        pulse, reference_complete_energy_j=10.0, candidate_complete_energy_j=10.0
    ).passed
    energy_only = c2.evaluate_activation_energy_mechanism(
        no_pulse, reference_complete_energy_j=10.0, candidate_complete_energy_j=9.0
    )
    assert energy_only.passed and energy_only.lower_complete_energy
    assert not c2.evaluate_activation_energy_mechanism(
        no_pulse, reference_complete_energy_j=10.0, candidate_complete_energy_j=10.0
    ).passed


def _power_terms(reported_system_power_w=14.876):
    return c2.PowerIntervalTerms(
        beams=(
            c2.BeamPowerTerms(INCUMBENT, (4.0, 2.0), 4.0, 0.5, 8.0),
            c2.BeamPowerTerms((100, 2), (3.0,), 3.0, 0.5, 6.0),
        ),
        active_beam_counts_by_satellite={100: 2},
        circuit_power_per_active_beam_w=0.338,
        baseband_power_per_active_satellite_w=0.2,
        reported_fixed_power_w=0.876,
        reported_system_power_w=reported_system_power_w,
    )


def test_complete_power_identity_covers_recurrence_max_pa_fixed_and_system_terms():
    result = c2.validate_power_identity(_power_terms())
    assert result.passed
    assert result.reconstructed_fixed_power_w == pytest.approx(0.876)
    assert result.reconstructed_system_power_w == pytest.approx(14.876)


def test_power_identity_catches_superseded_per_link_pa_charging():
    # Incorrect total: (4/0.5 + 2/0.5) + 3/0.5 + fixed = 18.876 W.
    result = c2.validate_power_identity(_power_terms(reported_system_power_w=18.876))
    assert not result.passed
    assert "system_power_mismatch" in result.reasons


@pytest.mark.parametrize(
    ("terms", "reason"),
    [
        (replace(_power_terms(), beams=(replace(_power_terms().beams[0], reported_beam_max_w=3.9), _power_terms().beams[1])), "beam_max_mismatch"),
        (replace(_power_terms(), beams=(replace(_power_terms().beams[0], reported_pa_supply_w=7.9), _power_terms().beams[1])), "pa_supply_mismatch"),
        (replace(_power_terms(), active_beam_counts_by_satellite={100: 1}), "active_beam_count_mismatch"),
    ],
)
def test_each_complete_power_component_identity_fails_closed(terms, reason):
    result = c2.validate_power_identity(terms)
    assert not result.passed
    assert any(reason in item for item in result.reasons)


ALLOWED_R2 = (0.0, -1.0, -2.0)


def _matrix(value=False):
    return [[value, value] for _ in range(4)]


def _reward_decision(
    reference_r2=((-1.0, 0.0), (0.0, -1.0), (0.0, 0.0), (0.0, 0.0)),
    candidate_r2=((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (-1.0, 0.0)),
    *,
    reference_served=None,
    candidate_served=None,
    reference_reentry=None,
    candidate_reentry=None,
    omit_release=False,
):
    reference_served = _matrix(True) if reference_served is None else reference_served
    candidate_served = _matrix(True) if candidate_served is None else candidate_served
    reference_reentry = _matrix(False) if reference_reentry is None else reference_reentry
    candidate_reentry = _matrix(False) if candidate_reentry is None else candidate_reentry
    report = None
    if not omit_release:
        report = c2.ReleaseReport(
            reference_focal_r2=reference_r2[3][0],
            candidate_focal_r2=candidate_r2[3][0],
            reference_system_r2=sum(reference_r2[3]),
            candidate_system_r2=sum(candidate_r2[3]),
        )
    return c2.evaluate_reward_release_service(
        reference_r2=reference_r2,
        candidate_r2=candidate_r2,
        allowed_r2_values=ALLOWED_R2,
        focal_user=0,
        reference_served=reference_served,
        candidate_served=candidate_served,
        reference_reentry=reference_reentry,
        candidate_reentry=candidate_reentry,
        release_report=report,
    )


def test_system_r2_can_pay_a_release_cost_when_strict_advantage_survives():
    result = _reward_decision()
    assert result.passed
    assert result.candidate_hold_r2 > result.reference_hold_r2
    assert result.candidate_full_r2 > result.reference_full_r2
    assert result.release.candidate_focal_r2 == -1.0


def test_focal_win_with_system_loss_and_delayed_only_event_fail():
    focal_win_system_loss = _reward_decision(
        reference_r2=((-1.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
        candidate_r2=((0.0, -2.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
    )
    assert "system_hold_r2_not_strictly_better" in focal_win_system_loss.reasons
    delayed_only = _reward_decision(
        reference_r2=((-1.0, 0.0), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
        candidate_r2=((0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (-1.0, 0.0)),
    )
    assert "system_full_r2_not_strictly_better" in delayed_only.reasons


def test_release_event_may_not_be_omitted():
    result = _reward_decision(omit_release=True)
    assert not result.passed
    assert "release_event_omitted" in result.reasons


def test_reward_service_guards_reject_truthy_nonboolean_receipt_values():
    malformed_served = _matrix(True)
    malformed_served[1][0] = 1
    with pytest.raises(ValueError, match="Boolean"):
        _reward_decision(candidate_served=malformed_served)


@pytest.mark.parametrize(("mutation", "reason"), [
    ("outage", "focal_outage"),
    ("reentry", "focal_reentry"),
    ("served_to_unserved", "served_to_unserved"),
])
def test_outage_reentry_and_served_to_unserved_transitions_fail(mutation, reason):
    reference_served = _matrix(True)
    candidate_served = _matrix(True)
    candidate_reentry = _matrix(False)
    if mutation == "outage":
        candidate_served[2][0] = False
    elif mutation == "reentry":
        candidate_reentry[2][0] = True
    else:
        candidate_served[1][1] = False
    result = _reward_decision(
        reference_served=reference_served,
        candidate_served=candidate_served,
        candidate_reentry=candidate_reentry,
    )
    assert not result.passed
    assert reason in result.reasons


def test_useful_bits_equality_is_allowed_with_positive_energy_saving_surplus():
    result = c2.evaluate_binary_proxies(
        reference_useful_bits=100.0,
        candidate_useful_bits=100.0,
        reference_energy_j=10.0,
        candidate_energy_j=9.0,
    )
    assert result.passed
    assert result.surplus_bits == pytest.approx(10.0)


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ((100.0, 100.0, 0.0, 9.0), "energy_not_strictly_positive"),
        ((100.0, 100.0, float("nan"), 9.0), "nonfinite_accumulation"),
        ((100.0, 100.0, 10.0, 10.0), "surplus_not_strictly_positive"),
        ((100.0, 100.0, 10.0, 10.000000000001), "surplus_not_strictly_positive"),
        ((100.0, 99.0, 10.0, 9.0), "useful_bits_loss"),
    ],
)
def test_energy_surplus_and_useful_bits_guards_have_no_epsilon_shortcuts(values, reason):
    result = c2.evaluate_binary_proxies(
        reference_useful_bits=values[0], candidate_useful_bits=values[1],
        reference_energy_j=values[2], candidate_energy_j=values[3],
    )
    assert not result.passed
    assert reason in result.reasons


def test_negative_useful_bits_fail_closed_before_surplus_arithmetic():
    result = c2.evaluate_binary_proxies(
        reference_useful_bits=-1.0,
        candidate_useful_bits=0.0,
        reference_energy_j=10.0,
        candidate_energy_j=9.0,
    )
    assert not result.passed
    assert result.reasons == ("useful_bits_negative",)


def _evidence(**changes):
    values = {field: True for field in c2._LAYER_FIELDS}
    values.update(changes)
    return c2.LayerEvidence(**values)


def test_layers_stop_at_first_failure_and_candidate_order_cannot_rank_proxies():
    failed = c2.evaluate_layers(_evidence(strict_system_r2=False))
    assert not failed.certified
    assert failed.first_failed_layer == "strict_system_r2"
    candidates_a = {INCUMBENT: _evidence(), RELOCATION: _evidence(), OTHER: _evidence(service_and_binary_proxies=False)}
    candidates_b = dict(reversed(tuple(candidates_a.items())))
    assert c2.certified_support(candidates_a) == c2.certified_support(candidates_b)
    assert c2.certified_support(candidates_a) == frozenset({INCUMBENT, RELOCATION})


def test_layers_reject_integer_or_string_surrogates_for_boolean_evidence():
    with pytest.raises(ValueError, match="Boolean"):
        c2.evaluate_layers(_evidence(strict_system_r2=1))


def test_control_arms_expose_only_their_declared_membership_and_c2_i_is_absent():
    hard_safe = [OTHER, INCUMBENT, RELOCATION]
    certified = [RELOCATION, INCUMBENT]
    assert c2.control_support(c2.ControlArm.PERSIST_RANDOM, hard_safe_support=hard_safe,
                              certified_choice_support=certified, incumbent_id=INCUMBENT) == frozenset(hard_safe)
    assert c2.control_support(c2.ControlArm.STAY, hard_safe_support=hard_safe,
                              certified_choice_support=certified, incumbent_id=INCUMBENT) == frozenset({INCUMBENT})
    assert c2.control_support(c2.ControlArm.CHURN_CERT_RANDOM, hard_safe_support=hard_safe,
                              certified_choice_support=certified, incumbent_id=INCUMBENT) == frozenset(certified)
    with pytest.raises(ValueError, match="absent"):
        c2.control_support(c2.ControlArm.LEARNED, hard_safe_support=hard_safe,
                           certified_choice_support=certified, incumbent_id=INCUMBENT)


def _floor_fixture():
    schedule = {partition: [f"p{partition}-a{index}" for index in range(4)] for partition in range(5)}
    rows = [
        c2.AnchorSupportRow(partition, anchor_id, frozenset({INCUMBENT, RELOCATION}))
        for partition, anchor_ids in schedule.items()
        for anchor_id in anchor_ids
    ]
    return schedule, rows


def test_support_floor_requires_each_partition_and_twenty_two_choice_anchors():
    schedule, rows = _floor_fixture()
    result = c2.aggregate_support_floor(rows, scheduled_anchor_ids_by_partition=schedule)
    assert result.passed
    assert result.qualifying_anchors_by_partition == {0: 4, 1: 4, 2: 4, 3: 4, 4: 4}
    assert result.pooled_qualifying_anchors == 20

    rows[0] = replace(rows[0], certified_choices=frozenset({INCUMBENT}))
    pooled_short = c2.aggregate_support_floor(rows, scheduled_anchor_ids_by_partition=schedule)
    assert not pooled_short.passed
    assert pooled_short.pooled_qualifying_anchors == 19

    for index, row in enumerate(rows):
        if row.partition == 4:
            rows[index] = replace(row, certified_choices=frozenset({INCUMBENT}))
    missing_partition = c2.aggregate_support_floor(
        rows, scheduled_anchor_ids_by_partition=schedule, minimum_pooled_two_choice_anchors=1
    )
    assert not missing_partition.passed
    assert missing_partition.qualifying_anchors_by_partition[4] == 0


def test_support_floor_never_imputes_an_unsupported_or_missing_anchor_row():
    schedule, rows = _floor_fixture()
    with pytest.raises(ValueError, match="exactly cover"):
        c2.aggregate_support_floor(rows[:-1], scheduled_anchor_ids_by_partition=schedule)
