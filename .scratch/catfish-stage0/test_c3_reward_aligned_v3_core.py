"""Focused deterministic fixtures for the pure C3 reward-aligned V3 core."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).with_name("c3_reward_aligned_v3_core.py")
spec = importlib.util.spec_from_file_location("c3_reward_aligned_v3_core", MODULE_PATH)
c3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = c3
spec.loader.exec_module(c3)


SOURCE = (100, 1)
DESTINATION = (100, 2)
OTHER = (200, 3)


def test_scalarized_main_uses_exact_weights_and_stable_masked_greedy_ties():
    # Q1-only chooses action 0; deployed scalarization chooses action 1.
    assert c3.masked_scalarized_main_action(
        [10.0, 9.0], [0.0, 10.0], [0.0, 0.0], [True, True],
        weights=(0.5, 0.3, 0.2),
    ) == 1
    assert c3.masked_scalarized_main_action(
        [1.0, 1.0], [1.0, 1.0], [1.0, 1.0], [True, True],
        weights=(0.5, 0.3, 0.2),
    ) == 0
    assert c3.masked_scalarized_main_action(
        [1.0], [1.0], [1.0], [False], weights=(0.5, 0.3, 0.2)
    ) is None


def test_scalarized_main_weight_drift_fails_before_inference():
    with pytest.raises(ValueError, match="drifted"):
        c3.masked_scalarized_main_action(
            [1.0], [1.0], [1.0], [True], weights=(1.0, 0.0, 0.0)
        )


def test_physical_id_remapping_survives_reordering_and_duplicates_fail_closed():
    assert c3.remap_physical_id([SOURCE, DESTINATION, OTHER], DESTINATION) == 1
    assert c3.remap_physical_id([OTHER, SOURCE, DESTINATION], DESTINATION) == 2
    with pytest.raises(ValueError, match="duplicate"):
        c3.unique_physical_id_map([SOURCE, DESTINATION, SOURCE])
    with pytest.raises(ValueError, match="not uniquely remappable"):
        c3.remap_physical_id([SOURCE, OTHER], DESTINATION)


def _forced(candidate_id=DESTINATION, **changes):
    values = dict(
        reference_physical_id=SOURCE,
        candidate_physical_id=candidate_id,
        reference_recurrence_power_w=0.5,
        candidate_recurrence_power_w=0.4,
        canonical_link_ceiling_w=1.0,
    )
    values.update(changes)
    return c3.ForcedInterval(**values)


def _grammar(**changes):
    values = dict(
        source_id=SOURCE,
        destination_id=DESTINATION,
        destination_already_active_without_focal=True,
        forced_intervals=[_forced()] * 3,
        reference_release_action=SOURCE,
        candidate_release_action=DESTINATION,
        reference_scalarized_main_action=SOURCE,
        candidate_scalarized_main_action=DESTINATION,
        release_present=True,
    )
    values.update(changes)
    return c3.validate_relocation_grammar(**values)


def test_exact_one_relocation_three_holds_and_scalarized_release_passes():
    result = _grammar()
    assert result.passed
    assert result.source_id == SOURCE and result.destination_id == DESTINATION


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"destination_id": OTHER}, "cross_satellite_destination"),
        ({"destination_already_active_without_focal": False}, "destination_not_already_active"),
        ({"forced_intervals": [_forced(), _forced((100, 9)), _forced()]}, "second_relocation_or_redraw"),
        ({"forced_intervals": [_forced(), _forced(hidden_fallback=True), _forced()]}, "hidden_fallback"),
        ({"forced_intervals": [_forced(), _forced(expired=True), _forced()]}, "early_expiry"),
        ({"forced_intervals": [_forced()] * 2}, "hold_window_incomplete"),
        ({"release_present": False}, "release_window_incomplete"),
        ({"candidate_scalarized_main_action": SOURCE}, "candidate_release_not_scalarized_main"),
    ],
)
def test_invalid_destination_redraw_fallback_expiry_or_short_release_fails(changes, reason):
    result = _grammar(**changes)
    assert not result.passed
    assert result.reason == reason


def test_one_nonfocal_physical_action_change_fails_even_with_equal_shape():
    reference = [[SOURCE, None], [DESTINATION, OTHER], [OTHER, None], [SOURCE, OTHER]]
    candidate = [list(row) for row in reference]
    assert c3.nonfocal_physical_identity(reference, candidate)
    candidate[2][0] = DESTINATION
    assert not c3.nonfocal_physical_identity(reference, candidate)


def test_grammar_flags_fail_closed_on_truthy_non_booleans():
    with pytest.raises(ValueError, match="release-present"):
        _grammar(release_present=1)
    with pytest.raises(ValueError, match="forced-interval flags"):
        _grammar(forced_intervals=[_forced(reference_served=1), _forced(), _forced()])


def _snapshot(associations, loads, r3_values):
    return c3.LoadSnapshot(
        served_associations=tuple(associations),
        reported_eligible_loads=loads,
        reported_active_beams=frozenset(loads),
        canonical_r3_by_user=tuple(r3_values),
    )


def _reference_load_snapshot():
    return _snapshot(
        [SOURCE, SOURCE, SOURCE, DESTINATION],
        {SOURCE: 3, DESTINATION: 1},
        [-3.0, -3.0, -3.0, -1.0],
    )


def _candidate_load_snapshot():
    return _snapshot(
        [DESTINATION, SOURCE, SOURCE, DESTINATION],
        {SOURCE: 2, DESTINATION: 2},
        [-2.0, -2.0, -2.0, -2.0],
    )


def test_load_reconstruction_squared_identity_and_exact_r3_delta_pass():
    reference = c3.validate_load_snapshot(_reference_load_snapshot())
    candidate = c3.validate_load_snapshot(_candidate_load_snapshot())
    assert reference.passed and reference.canonical_r3_total == -10.0
    assert candidate.passed and candidate.canonical_r3_total == -8.0
    relocation = c3.validate_relocation_load_identity(
        source_id=SOURCE, destination_id=DESTINATION,
        reference=_reference_load_snapshot(), candidate=_candidate_load_snapshot(),
    )
    assert relocation.passed
    assert relocation.load_gap == 2
    assert relocation.expected_system_r3_delta == 2
    assert relocation.reported_system_r3_delta == 2.0


@pytest.mark.parametrize(
    ("snapshot", "reason"),
    [
        (
            replace(_reference_load_snapshot(), reported_eligible_loads={SOURCE: 2, DESTINATION: 2}),
            "eligible_load_reconstruction_mismatch",
        ),
        (
            replace(_reference_load_snapshot(), reported_active_beams=frozenset({SOURCE})),
            "positive_load_active_beam_mismatch",
        ),
        (
            replace(_reference_load_snapshot(), canonical_r3_by_user=(-2.0, -3.0, -3.0, -1.0)),
            "canonical_r3_per_user_mismatch",
        ),
    ],
)
def test_load_snapshot_fails_reconstruction_active_set_or_reward_rewrite(snapshot, reason):
    result = c3.validate_load_snapshot(snapshot)
    assert not result.passed
    assert reason in result.reasons


def test_off_by_one_candidate_map_and_non_strict_gap_fail():
    off_by_one = replace(
        _candidate_load_snapshot(),
        served_associations=(DESTINATION, DESTINATION, DESTINATION, DESTINATION),
        reported_eligible_loads={DESTINATION: 4},
        reported_active_beams=frozenset({DESTINATION}),
        canonical_r3_by_user=(-4.0, -4.0, -4.0, -4.0),
    )
    result = c3.validate_relocation_load_identity(
        source_id=SOURCE, destination_id=DESTINATION,
        reference=_reference_load_snapshot(), candidate=off_by_one,
    )
    assert "not_exact_source_minus_one_destination_plus_one" in result.reasons

    reference = _snapshot(
        [SOURCE, SOURCE, DESTINATION, DESTINATION],
        {SOURCE: 2, DESTINATION: 2},
        [-2.0, -2.0, -2.0, -2.0],
    )
    candidate = _snapshot(
        [DESTINATION, SOURCE, DESTINATION, DESTINATION],
        {SOURCE: 1, DESTINATION: 3},
        [-3.0, -1.0, -3.0, -3.0],
    )
    non_strict = c3.validate_relocation_load_identity(
        source_id=SOURCE, destination_id=DESTINATION,
        reference=reference, candidate=candidate,
    )
    assert "strict_load_gap_failed" in non_strict.reasons
    assert "canonical_r3_delta_not_strictly_positive" in non_strict.reasons


def _power(scale=1.0, *, reported_system=None):
    fixed = 0.876
    system = fixed + 14.0 * scale if reported_system is None else reported_system
    return c3.PowerIntervalTerms(
        beams=(
            c3.BeamPowerTerms(SOURCE, (4.0 * scale, 2.0 * scale), 4.0 * scale, 0.5, 8.0 * scale),
            c3.BeamPowerTerms(DESTINATION, (3.0 * scale,), 3.0 * scale, 0.5, 6.0 * scale),
        ),
        active_beam_counts_by_satellite={100: 2},
        circuit_power_per_active_beam_w=0.338,
        baseband_power_per_active_satellite_w=0.2,
        reported_fixed_power_w=fixed,
        reported_system_power_w=system,
    )


def test_complete_supplied_power_identity_covers_recurrence_pa_and_fixed_terms():
    result = c3.validate_power_identity(_power())
    assert result.passed
    assert result.reconstructed_fixed_power_w == pytest.approx(0.876)
    assert result.reconstructed_system_power_w == pytest.approx(14.876)


def test_superseded_per_link_pa_total_and_component_mismatches_fail():
    wrong_total = c3.validate_power_identity(_power(reported_system=18.876))
    assert "system_power_mismatch" in wrong_total.reasons
    wrong_max = c3.validate_power_identity(
        replace(_power(), beams=(replace(_power().beams[0], reported_beam_max_w=3.9), _power().beams[1]))
    )
    assert any("beam_max_mismatch" in reason for reason in wrong_max.reasons)
    wrong_supply = c3.validate_power_identity(
        replace(_power(), beams=(replace(_power().beams[0], reported_pa_supply_w=7.9), _power().beams[1]))
    )
    assert any("pa_supply_mismatch" in reason for reason in wrong_supply.reasons)
    wrong_count = c3.validate_power_identity(replace(_power(), active_beam_counts_by_satellite={100: 1}))
    assert "active_beam_count_mismatch" in wrong_count.reasons


def test_missing_recurrence_and_omitted_fixed_components_fail_power_identity():
    missing_recurrence = c3.validate_power_identity(
        replace(
            _power(),
            beams=(replace(_power().beams[0], recurrence_outputs_w=()), _power().beams[1]),
        )
    )
    assert any("missing_recurrence_output" in reason for reason in missing_recurrence.reasons)

    omitted_circuit = c3.validate_power_identity(
        replace(_power(), circuit_power_per_active_beam_w=0.0)
    )
    assert "fixed_power_mismatch" in omitted_circuit.reasons
    omitted_baseband = c3.validate_power_identity(
        replace(_power(), baseband_power_per_active_satellite_w=0.0)
    )
    assert "fixed_power_mismatch" in omitted_baseband.reasons


@pytest.mark.parametrize("field", ["reported_beam_max_w", "reported_pa_efficiency", "reported_system_power_w"])
def test_power_identity_rejects_boolean_numeric_fields(field):
    terms = _power()
    if field == "reported_system_power_w":
        terms = replace(terms, reported_system_power_w=True)
    else:
        terms = replace(
            terms,
            beams=(replace(terms.beams[0], **{field: True}), terms.beams[1]),
        )
    with pytest.raises(ValueError, match="finite real"):
        c3.validate_power_identity(terms)


def test_four_offset_power_nonincrease_and_one_strict_decrease_passes():
    reference = [_power()] * 4
    candidate = [_power(0.9), _power(), _power(), _power()]
    result = c3.evaluate_power_window(reference, candidate)
    assert result.passed
    assert result.strict_decrease_offsets == (0,)
    assert 0.0 < result.candidate_energy_j < result.reference_energy_j


def test_equal_power_passes_this_layer_but_release_increase_and_nonpositive_energy_fail():
    equal = c3.evaluate_power_window([_power()] * 4, [_power()] * 4)
    assert equal.passed
    assert equal.strict_decrease_offsets == ()
    release_increase = c3.evaluate_power_window(
        [_power()] * 4, [_power(0.9), _power(), _power(), _power(1.1)]
    )
    assert "offset_3:candidate_power_increase" in release_increase.reasons

    zero = c3.PowerIntervalTerms(
        beams=(), active_beam_counts_by_satellite={},
        circuit_power_per_active_beam_w=0.338,
        baseband_power_per_active_satellite_w=0.2,
        reported_fixed_power_w=0.0, reported_system_power_w=0.0,
    )
    zero_window = c3.evaluate_power_window([zero] * 4, [zero] * 4)
    assert "certificate_energy_not_finite_positive" in zero_window.reasons


def _bool_matrix(value, users=4):
    return [[value] * users for _ in range(4)]


def _event_matrix(value, users=4):
    return [[value] * users for _ in range(4)]


REFERENCE_R3 = tuple([(-3.0, -3.0, -3.0, -1.0)] * 3 + [(-2.0, -2.0, -2.0, -2.0)])
CANDIDATE_R3 = tuple([(-2.0, -2.0, -2.0, -2.0)] * 3 + [(-2.0, -2.0, -2.0, -2.0)])


def _reward_guard(
    reference_r3=REFERENCE_R3,
    candidate_r3=CANDIDATE_R3,
    *,
    reference_served=None,
    candidate_served=None,
    reference_reentry=None,
    candidate_reentry=None,
    reference_events=None,
    candidate_events=None,
    omit_release=False,
):
    reference_served = _bool_matrix(True) if reference_served is None else reference_served
    candidate_served = _bool_matrix(True) if candidate_served is None else candidate_served
    reference_reentry = _bool_matrix(False) if reference_reentry is None else reference_reentry
    candidate_reentry = _bool_matrix(False) if candidate_reentry is None else candidate_reentry
    reference_events = _event_matrix(c3.EventClass.NONE) if reference_events is None else reference_events
    if candidate_events is None:
        candidate_events = _event_matrix(c3.EventClass.NONE)
        candidate_events[0][0] = c3.EventClass.INTRA_SATELLITE
    report = None
    if not omit_release:
        report = c3.ReleaseReport(
            reference_focal_r3=reference_r3[3][0],
            candidate_focal_r3=candidate_r3[3][0],
            reference_system_r3=sum(reference_r3[3]),
            candidate_system_r3=sum(candidate_r3[3]),
        )
    return c3.evaluate_reward_service_events(
        reference_r3=reference_r3, candidate_r3=candidate_r3, focal_user=0,
        reference_served=reference_served, candidate_served=candidate_served,
        reference_reentry=reference_reentry, candidate_reentry=candidate_reentry,
        reference_events=reference_events, candidate_events=candidate_events,
        release_report=report,
    )


def test_system_r3_is_strict_during_hold_and_survives_first_release():
    result = _reward_guard()
    assert result.passed
    assert result.candidate_hold_r3 > result.reference_hold_r3
    assert result.candidate_full_r3 > result.reference_full_r3


def test_focal_win_system_loss_delayed_erasure_and_omitted_release_fail():
    focal_win_system_loss = _reward_guard(
        reference_r3=((-3.0, -1.0), (-1.0, -1.0), (-1.0, -1.0), (-1.0, -1.0)),
        candidate_r3=((-1.0, -4.0), (-1.0, -1.0), (-1.0, -1.0), (-1.0, -1.0)),
        reference_served=_bool_matrix(True, 2), candidate_served=_bool_matrix(True, 2),
        reference_reentry=_bool_matrix(False, 2), candidate_reentry=_bool_matrix(False, 2),
        reference_events=_event_matrix(c3.EventClass.NONE, 2),
        candidate_events=[
            [c3.EventClass.INTRA_SATELLITE, c3.EventClass.NONE],
            [c3.EventClass.NONE, c3.EventClass.NONE],
            [c3.EventClass.NONE, c3.EventClass.NONE],
            [c3.EventClass.NONE, c3.EventClass.NONE],
        ],
    )
    assert "system_hold_r3_not_strictly_better" in focal_win_system_loss.reasons

    erased_release = list(CANDIDATE_R3)
    erased_release[3] = (-8.0, -2.0, -2.0, -2.0)  # consumes the six-point hold advantage
    erased = _reward_guard(candidate_r3=tuple(erased_release))
    assert "system_full_r3_not_strictly_better" in erased.reasons
    assert "release_row_omitted" in _reward_guard(omit_release=True).reasons


@pytest.mark.parametrize(("mutation", "reason"), [
    ("outage", "focal_outage"),
    ("reentry", "focal_reentry"),
    ("served_to_unserved", "served_to_unserved"),
    ("event", "undeclared_candidate_event"),
    ("nonfocal_event", "undeclared_candidate_event"),
])
def test_service_reentry_served_transition_and_undeclared_event_fail(mutation, reason):
    reference_served = _bool_matrix(True)
    candidate_served = _bool_matrix(True)
    candidate_reentry = _bool_matrix(False)
    candidate_events = _event_matrix(c3.EventClass.NONE)
    candidate_events[0][0] = c3.EventClass.INTRA_SATELLITE
    if mutation == "outage":
        candidate_served[2][0] = False
    elif mutation == "reentry":
        candidate_reentry[2][0] = True
    elif mutation == "served_to_unserved":
        candidate_served[1][1] = False
    elif mutation == "nonfocal_event":
        candidate_events[2][1] = c3.EventClass.INTRA_SATELLITE
    else:
        candidate_events[3][0] = c3.EventClass.INTER_SATELLITE
    result = _reward_guard(
        reference_served=reference_served, candidate_served=candidate_served,
        candidate_reentry=candidate_reentry, candidate_events=candidate_events,
    )
    assert not result.passed
    assert reason in result.reasons


def _identity_kwargs():
    actions = [[SOURCE, None], [DESTINATION, OTHER], [OTHER, None], [SOURCE, OTHER]]
    beams = [frozenset({SOURCE, DESTINATION})] * 4
    satellites = [frozenset({100})] * 4
    return dict(
        reference_nonfocal_actions=actions,
        candidate_nonfocal_actions=[list(row) for row in actions],
        reference_active_beams=beams,
        candidate_active_beams=beams,
        reference_active_satellites=satellites,
        candidate_active_satellites=satellites,
        preview_commit_equal=[True] * 4,
    )


def test_full_window_nonfocal_active_set_and_preview_commit_identity():
    assert c3.evaluate_hard_safe_identity(**_identity_kwargs()).passed
    values = _identity_kwargs()
    values["candidate_active_beams"] = list(values["candidate_active_beams"])
    values["candidate_active_beams"][2] = frozenset({SOURCE})
    result = c3.evaluate_hard_safe_identity(**values)
    assert "offset_2:active_beam_set_mismatch" in result.reasons
    values = _identity_kwargs()
    values["preview_commit_equal"] = [True, False, True, True]
    assert "offset_1:preview_commit_mismatch" in c3.evaluate_hard_safe_identity(**values).reasons
    values = _identity_kwargs()
    values["candidate_active_satellites"] = [frozenset({100, 999})] * 4
    projection = c3.evaluate_hard_safe_identity(**values)
    assert "offset_0:candidate_active_satellite_projection_mismatch" in projection.reasons


def test_useful_bits_equality_passes_only_with_strict_positive_surplus():
    result = c3.evaluate_binary_proxies(
        reference_useful_bits=100.0, candidate_useful_bits=100.0,
        reference_energy_j=10.0, candidate_energy_j=9.0,
    )
    assert result.passed and result.surplus_bits == pytest.approx(10.0)


def test_power_tied_candidate_requires_strict_useful_bit_gain_for_surplus():
    tied = c3.evaluate_binary_proxies(
        reference_useful_bits=100.0, candidate_useful_bits=100.0,
        reference_energy_j=10.0, candidate_energy_j=10.0,
    )
    assert not tied.passed
    assert "surplus_not_strictly_positive" in tied.reasons
    bits_gain = c3.evaluate_binary_proxies(
        reference_useful_bits=100.0, candidate_useful_bits=101.0,
        reference_energy_j=10.0, candidate_energy_j=10.0,
    )
    assert bits_gain.passed and bits_gain.surplus_bits == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ((100.0, 99.0, 10.0, 9.0), "useful_bits_loss"),
        ((100.0, 100.0, 0.0, 9.0), "energy_not_strictly_positive"),
        ((100.0, 100.0, 10.0, 10.0), "surplus_not_strictly_positive"),
        ((100.0, 100.0, 10.0, 10.000000000001), "surplus_not_strictly_positive"),
    ],
)
def test_binary_proxy_has_no_epsilon_or_tolerance_shortcuts(values, reason):
    result = c3.evaluate_binary_proxies(
        reference_useful_bits=values[0], candidate_useful_bits=values[1],
        reference_energy_j=values[2], candidate_energy_j=values[3],
    )
    assert not result.passed
    assert reason in result.reasons


@pytest.mark.parametrize("bad", [True, "100", float("inf")])
def test_binary_proxy_rejects_nonreal_boolean_or_nonfinite_accumulations(bad):
    with pytest.raises(ValueError, match="finite real"):
        c3.evaluate_binary_proxies(
            reference_useful_bits=bad, candidate_useful_bits=100.0,
            reference_energy_j=10.0, candidate_energy_j=9.0,
        )


def test_binary_proxy_rejects_negative_useful_bits():
    result = c3.evaluate_binary_proxies(
        reference_useful_bits=-1.0, candidate_useful_bits=0.0,
        reference_energy_j=10.0, candidate_energy_j=9.0,
    )
    assert not result.passed
    assert "useful_bits_negative" in result.reasons


def _evidence(**changes):
    values = {field: True for field in c3._LAYER_FIELDS}
    values.update(changes)
    return c3.LayerEvidence(**values)


def test_support_layers_are_nested_and_order_invariant():
    candidates = {
        SOURCE: _evidence(),
        DESTINATION: _evidence(complete_power=False),
        OTHER: _evidence(strict_load=False),
    }
    first = c3.support_sets(candidates)
    second = c3.support_sets(dict(reversed(tuple(candidates.items()))))
    assert first == second
    assert first.safe == frozenset({SOURCE, DESTINATION, OTHER})
    assert first.load == frozenset({SOURCE, DESTINATION})
    assert first.certified == frozenset({SOURCE})
    stopped = c3.evaluate_layers(candidates[DESTINATION])
    assert stopped.first_failed_layer == "complete_power" and not stopped.certified


def test_safe_load_cert_and_gap_controls_use_exact_declared_supports():
    supports = c3.SupportSets(
        safe=frozenset({SOURCE, DESTINATION, OTHER}),
        load=frozenset({SOURCE, DESTINATION}),
        certified=frozenset({SOURCE}),
    )
    assert c3.control_support(c3.ControlArm.SAFE_RANDOM, supports) == supports.safe
    assert c3.control_support(c3.ControlArm.LOAD_RANDOM, supports) == supports.load
    assert c3.control_support(c3.ControlArm.CERT_RANDOM, supports) == supports.certified
    assert c3.control_support(c3.ControlArm.GAP, supports) == supports.certified
    with pytest.raises(ValueError, match="absent"):
        c3.control_support(c3.ControlArm.LEARNED, supports)
    with pytest.raises(ValueError, match="nested"):
        c3.control_support(
            c3.ControlArm.CERT_RANDOM,
            c3.SupportSets(frozenset({SOURCE}), frozenset({SOURCE}), frozenset({OTHER})),
        )


def test_gap_ranks_direct_load_gap_only_then_physical_id():
    ids = [(100, 9), (100, 2), (100, 5)]
    assert c3.select_c3_gap(
        certified_support=ids,
        cumulative_direct_load_gap={(100, 9): 8, (100, 2): 8, (100, 5): 7},
    ) == (100, 2)
    assert c3.select_c3_gap(
        certified_support=list(reversed(ids)),
        cumulative_direct_load_gap={(100, 5): 7, (100, 2): 8, (100, 9): 8},
    ) == (100, 2)
    with pytest.raises(ValueError, match="exactly cover"):
        c3.select_c3_gap(
            certified_support=ids,
            cumulative_direct_load_gap={(100, 9): 8, (100, 2): 8},
        )
    with pytest.raises(ValueError, match="duplicate"):
        c3.select_c3_gap(
            certified_support=[(100, 2), (100, 2)],
            cumulative_direct_load_gap={(100, 2): 8},
        )


def test_observational_alias_is_explicit_and_cannot_be_silently_consumer_safe():
    main_aliased = [
        c3.AliasState((5.0,), (1.0, 2.0), frozenset({SOURCE})),
        c3.AliasState((6.0,), (1.0, 2.0), frozenset({DESTINATION})),
    ]
    specialist_aliased = [
        c3.AliasState((5.0,), (1.0, 2.0), frozenset({SOURCE})),
        c3.AliasState((5.0,), (1.0, 3.0), frozenset({DESTINATION})),
    ]
    main_decision = c3.observational_alias_decision(main_aliased)
    specialist_decision = c3.observational_alias_decision(specialist_aliased)
    assert main_decision.main_unresolved
    assert not main_decision.specialist_unresolved
    assert specialist_decision.specialist_unresolved
    assert not specialist_decision.main_unresolved


def test_alias_inputs_reject_boolean_string_empty_and_width_drift():
    for observation in ((True,), ("1",), ()):
        with pytest.raises(ValueError):
            c3.observational_alias_decision(
                [c3.AliasState(observation, (1.0,), frozenset({SOURCE}))]
            )
    with pytest.raises(ValueError, match="fixed width"):
        c3.observational_alias_decision([
            c3.AliasState((1.0,), (1.0,), frozenset({SOURCE})),
            c3.AliasState((1.0, 2.0), (1.0,), frozenset({DESTINATION})),
        ])


def _floor_fixture():
    schedule = {
        partition: [f"p{partition}-a{index}" for index in range(4)]
        for partition in range(5)
    }
    rows = [
        c3.AnchorSupportRow(
            partition, anchor_id, frozenset({SOURCE, DESTINATION})
        )
        for partition, anchor_ids in schedule.items()
        for anchor_id in anchor_ids
    ]
    return schedule, rows


def test_support_floor_requires_every_partition_and_twenty_two_choice_anchors():
    schedule, rows = _floor_fixture()
    passed = c3.aggregate_support_floor(
        rows, scheduled_anchor_ids_by_partition=schedule
    )
    assert passed.passed
    assert passed.qualifying_anchors_by_partition == {
        0: 4, 1: 4, 2: 4, 3: 4, 4: 4
    }
    assert passed.pooled_qualifying_anchors == 20

    rows[0] = replace(rows[0], certified_choices=frozenset({SOURCE}))
    pooled_short = c3.aggregate_support_floor(
        rows, scheduled_anchor_ids_by_partition=schedule
    )
    assert not pooled_short.passed
    assert pooled_short.pooled_qualifying_anchors == 19

    for index, row in enumerate(rows):
        if row.partition == 4:
            rows[index] = replace(row, certified_choices=frozenset({SOURCE}))
    missing_partition = c3.aggregate_support_floor(
        rows,
        scheduled_anchor_ids_by_partition=schedule,
        minimum_pooled_two_choice_anchors=1,
    )
    assert not missing_partition.passed
    assert missing_partition.qualifying_anchors_by_partition[4] == 0


def test_support_floor_requires_exact_rows_and_strict_floor_types():
    schedule, rows = _floor_fixture()
    with pytest.raises(ValueError, match="exactly cover"):
        c3.aggregate_support_floor(
            rows[:-1], scheduled_anchor_ids_by_partition=schedule
        )
    with pytest.raises(ValueError, match="positive integer"):
        c3.aggregate_support_floor(
            rows,
            scheduled_anchor_ids_by_partition=schedule,
            minimum_pooled_two_choice_anchors=True,
        )
    malformed = list(rows)
    malformed[0] = replace(malformed[0], certified_choices={SOURCE, DESTINATION})
    with pytest.raises(ValueError, match="frozenset"):
        c3.aggregate_support_floor(
            malformed, scheduled_anchor_ids_by_partition=schedule
        )


def _composite_parts(**changes):
    load = c3.validate_relocation_load_identity(
        source_id=SOURCE,
        destination_id=DESTINATION,
        reference=_reference_load_snapshot(),
        candidate=_candidate_load_snapshot(),
    )
    values = dict(
        scheduled_anchor=True,
        qualifying_main_anchor=True,
        grammar=_grammar(),
        hard_safe=c3.evaluate_hard_safe_identity(**_identity_kwargs()),
        hold_loads=(load, load, load),
        power=c3.evaluate_power_window([_power()] * 4, [_power(0.9)] * 4),
        binary_proxies=c3.evaluate_binary_proxies(
            reference_useful_bits=100.0,
            candidate_useful_bits=100.0,
            reference_energy_j=100.0,
            candidate_energy_j=90.0,
        ),
        through_release=_reward_guard(),
    )
    values.update(changes)
    return c3.CandidateCertificateParts(**values)


def test_top_level_certificate_composes_all_frozen_layers():
    result = c3.compose_candidate_certificate(_composite_parts())
    assert result.passed
    assert result.first_failed_layer is None
    assert c3.evaluate_layers(result.layer_evidence).certified


def test_top_level_certificate_retains_first_failed_layer_and_offset():
    load_failure = replace(
        _composite_parts().hold_loads[1],
        passed=False,
        reasons=("strict_load_gap_failed",),
    )
    load_result = c3.compose_candidate_certificate(
        _composite_parts(
            hold_loads=(
                _composite_parts().hold_loads[0],
                load_failure,
                _composite_parts().hold_loads[2],
            )
        )
    )
    assert load_result.first_failed_layer == "strict_load"
    assert load_result.first_failed_offset == 1

    power_failure = c3.evaluate_power_window(
        [_power()] * 4, [_power(), _power(), _power(), _power(1.1)]
    )
    power_result = c3.compose_candidate_certificate(
        _composite_parts(power=power_failure)
    )
    assert power_result.first_failed_layer == "complete_power"
    assert power_result.first_failed_offset == 3


def test_top_level_certificate_fails_earliest_anchor_and_rejects_short_load_window():
    result = c3.compose_candidate_certificate(
        _composite_parts(
            scheduled_anchor=False,
            power=c3.evaluate_power_window(
                [_power()] * 4, [_power(), _power(), _power(), _power(1.1)]
            ),
        )
    )
    assert result.first_failed_layer == "scheduled_anchor"
    with pytest.raises(ValueError, match="offsets 0 through 2"):
        c3.compose_candidate_certificate(
            _composite_parts(hold_loads=_composite_parts().hold_loads[:2])
        )
