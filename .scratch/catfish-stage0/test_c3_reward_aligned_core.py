"""Deterministic tests for the pure reward-aligned C3 Stage-0 core."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("c3_reward_aligned_core.py")
spec = importlib.util.spec_from_file_location("c3_reward_aligned_core", MODULE_PATH)
c3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = c3
spec.loader.exec_module(c3)


SOURCE = (8, 1)
DESTINATION = (8, 2)


def test_physical_ids_are_exact_nonnegative_integer_pairs():
    assert c3.validate_physical_id((8, 2)) == (8, 2)
    for malformed in ([8, 2], (8,), (8, 2, 3), (8.0, 2), (True, 2), (-1, 2)):
        with pytest.raises(ValueError, match="physical ID"):
            c3.validate_physical_id(malformed)


def test_candidate_pair_is_distinct_and_same_satellite():
    assert c3.validate_candidate_pair(SOURCE, DESTINATION) == (SOURCE, DESTINATION)
    with pytest.raises(ValueError, match="same satellite"):
        c3.validate_candidate_pair(SOURCE, (9, 2))
    with pytest.raises(ValueError, match="differ"):
        c3.validate_candidate_pair(SOURCE, SOURCE)


def test_nonfocal_action_map_is_complete_and_strict():
    complete = {user: SOURCE for user in range(1, 100)}
    assert c3.validate_nonfocal_action_map(
        complete, focal_user_id=0, expected_user_count=100
    ) == complete

    missing = dict(complete)
    missing.pop(99)
    with pytest.raises(ValueError, match="complete"):
        c3.validate_nonfocal_action_map(
            missing, focal_user_id=0, expected_user_count=100
        )
    malformed = dict(complete)
    malformed[1] = (8.0, 1)
    with pytest.raises(ValueError, match="physical ID"):
        c3.validate_nonfocal_action_map(
            malformed, focal_user_id=0, expected_user_count=100
        )


def test_event_classes_are_explicit_and_certificate_sequence_is_fixed():
    assert c3.expected_certificate_event("reference", 0) is c3.EventClass.NONE
    assert c3.expected_certificate_event("candidate", 0) is c3.EventClass.PHI1
    assert c3.expected_certificate_event("candidate", 2) is c3.EventClass.NONE
    with pytest.raises(ValueError, match="event"):
        c3.validate_event_class("mystery")


def _power_snapshot(
    total: float = 7.414,
    *,
    residual: float = 0.0,
    supply: dict | None = None,
) -> object:
    if supply is None:
        supply = {SOURCE: 1.0, DESTINATION: 2.0, (9, 1): 3.0}
    return c3.PowerSnapshot(
        supply_power_w_by_beam=supply,
        radiating_beams_by_satellite={8: 2, 9: 1},
        reported_fixed_power_w=1.414,
        reported_system_power_w=total,
        pa_identity_residual_w=residual,
    )


def _power_with_total(total: float, *, residual: float = 0.0) -> object:
    fixed = 1.414
    supply_total = total - fixed
    return c3.PowerSnapshot(
        supply_power_w_by_beam={
            SOURCE: supply_total / 3.0,
            DESTINATION: supply_total / 3.0,
            (9, 1): supply_total / 3.0,
        },
        radiating_beams_by_satellite={8: 2, 9: 1},
        reported_fixed_power_w=fixed,
        reported_system_power_w=total,
        pa_identity_residual_w=residual,
    )


def test_full_system_power_is_recomputed_from_beams_and_satellites():
    snapshot = _power_snapshot()
    result = c3.recompute_system_power(snapshot)
    assert result.fixed_power_w == pytest.approx(1.414)
    assert result.system_power_w == pytest.approx(7.414)
    assert c3.validate_power_snapshot(snapshot) == ()


@pytest.mark.parametrize(
    ("snapshot", "reason"),
    [
        (_power_snapshot(total=7.5), "reported_system_power_mismatch"),
        (_power_snapshot(residual=1e-4), "pa_identity_failed"),
        (
            _power_snapshot(
                supply={SOURCE: float("nan"), DESTINATION: 2.0, (9, 1): 3.0}
            ),
            "malformed",
        ),
    ],
)
def test_power_snapshot_malformed_or_inconsistent_inputs_fail_closed(snapshot, reason):
    reasons = c3.validate_power_snapshot(snapshot)
    assert any(reason in item for item in reasons)


def test_power_recomputation_rejects_caller_substitution_of_frozen_constants():
    snapshot = c3.PowerSnapshot(
        **{
            **_power_snapshot().__dict__,
            "circuit_power_per_beam_w": 0.0,
        }
    )
    reasons = c3.validate_power_snapshot(snapshot)
    assert "circuit_power_constant_mismatch" in reasons
    assert c3.recompute_system_power(snapshot).system_power_w == pytest.approx(7.414)


def test_radiating_beam_power_must_be_strictly_positive():
    snapshot = c3.PowerSnapshot(
        supply_power_w_by_beam={SOURCE: 0.0, DESTINATION: 2.0, (9, 1): 3.0},
        radiating_beams_by_satellite={8: 2, 9: 1},
        reported_fixed_power_w=1.414,
        reported_system_power_w=6.414,
        pa_identity_residual_w=0.0,
    )
    assert any("strictly positive" in reason for reason in c3.validate_power_snapshot(snapshot))


def _interval(
    h: int,
    *,
    source_load: int = 4,
    destination_load: int = 1,
    reference_power: float = 10.0,
    candidate_power: float = 9.0,
    candidate_loads: dict | None = None,
    nonfocal_match: bool = True,
    pa_residual: float = 0.0,
) -> object:
    reference_loads = {
        SOURCE: source_load,
        DESTINATION: destination_load,
        (9, 1): 100 - source_load - destination_load,
    }
    if candidate_loads is None:
        candidate_loads = c3.expected_candidate_loads(
            reference_loads,
            source_id=SOURCE,
            destination_id=DESTINATION,
        )
    reference_actions = {}
    next_user = 1
    for _ in range(source_load - 1):
        reference_actions[next_user] = SOURCE
        next_user += 1
    for _ in range(destination_load):
        reference_actions[next_user] = DESTINATION
        next_user += 1
    while next_user < 100:
        reference_actions[next_user] = (9, 1)
        next_user += 1
    candidate_actions = dict(reference_actions)
    if not nonfocal_match:
        candidate_actions[1] = DESTINATION
    return c3.ForecastInterval(
        reference_loads=reference_loads,
        candidate_loads=candidate_loads,
        reference_r3_total=c3.canonical_r3_total(reference_loads),
        candidate_r3_total=c3.canonical_r3_total(candidate_loads),
        reference_power=_power_with_total(reference_power, residual=pa_residual),
        candidate_power=_power_with_total(candidate_power, residual=pa_residual),
        reference_nonfocal_actions=reference_actions,
        candidate_nonfocal_actions=candidate_actions,
        reference_served_users=tuple(range(100)),
        candidate_served_users=tuple(range(100)),
        reference_active_beams=(SOURCE, DESTINATION, (9, 1)),
        candidate_active_beams=(SOURCE, DESTINATION, (9, 1)),
        reference_active_satellites=(8, 9),
        candidate_active_satellites=(8, 9),
        reference_event=c3.EventClass.NONE,
        candidate_event=(c3.EventClass.PHI1 if h == 0 else c3.EventClass.NONE),
    )


def _certificate(**overrides) -> object:
    rows = [_interval(h, **overrides) for h in range(3)]
    return c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=rows,
        focal_user_id=0,
        expected_user_count=100,
    )


def test_integer_load_condition_matches_exact_r3_delta_exhaustively():
    for source in range(1, 9):
        for destination in range(0, 9):
            delta = c3.expected_one_user_r3_delta(source, destination)
            assert c3.strict_load_improvement(source, destination) == (
                source >= destination + 2
            )
            assert (delta > 0) == (source >= destination + 2)


@pytest.mark.parametrize("malformed", [True, 4.0, "4"])
def test_load_identity_helpers_reject_numeric_coercion(malformed):
    with pytest.raises(ValueError, match="exact integers"):
        c3.expected_one_user_r3_delta(malformed, 1)


def test_candidate_load_helper_requires_a_same_satellite_physical_pair():
    with pytest.raises(ValueError, match="same satellite"):
        c3.expected_candidate_loads(
            {SOURCE: 4, (9, 2): 1},
            source_id=SOURCE,
            destination_id=(9, 2),
        )


def test_candidate_load_map_and_both_r3_identities_are_exact():
    reference = {SOURCE: 4, DESTINATION: 1, (9, 1): 2}
    candidate = c3.expected_candidate_loads(
        reference,
        source_id=SOURCE,
        destination_id=DESTINATION,
    )
    assert candidate == {SOURCE: 3, DESTINATION: 2, (9, 1): 2}
    assert (
        c3.canonical_r3_total(candidate) - c3.canonical_r3_total(reference)
        == c3.expected_one_user_r3_delta(4, 1)
        == 4
    )


def test_joint_certificate_accepts_load_and_power_without_score_fusion():
    result = _certificate()
    assert result.hard_safe
    assert result.strict_load
    assert result.persistent_power
    assert result.joint
    assert result.reasons == ()
    assert result.load_gap_score == 9
    assert result.power_relief_j == pytest.approx(3 * 30.08)
    assert result.power_delta_w == pytest.approx((1.0, 1.0, 1.0))
    assert {entry.name: entry.passed for entry in result.guard_ledger} == {
        "physical_pair": True,
        "three_interval_horizon": True,
        "hard_safe": True,
        "strict_load": True,
        "persistent_power": True,
        "joint": True,
    }


def test_certificate_rejects_cross_satellite_before_support_can_be_created():
    with pytest.raises(ValueError, match="same satellite"):
        c3.certify_candidate(
            source_id=SOURCE,
            candidate_id=(9, 2),
            intervals=[_interval(h) for h in range(3)],
            focal_user_id=0,
            expected_user_count=100,
        )


def test_certificate_requires_exactly_three_intervals():
    with pytest.raises(ValueError, match="exactly three"):
        c3.certify_candidate(
            source_id=SOURCE,
            candidate_id=DESTINATION,
            intervals=[_interval(0), _interval(1)],
            focal_user_id=0,
            expected_user_count=100,
        )


def test_certificate_event_mismatch_fails_hard_safe_layer():
    row = _interval(0)
    malformed = c3.ForecastInterval(
        **{**row.__dict__, "candidate_event": c3.EventClass.PHI2}
    )
    result = c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=[malformed, _interval(1), _interval(2)],
        focal_user_id=0,
        expected_user_count=100,
    )
    assert not result.hard_safe
    assert any("candidate_event_mismatch" in reason for reason in result.reasons)


def test_incomplete_nonfocal_map_is_a_fail_closed_hard_safe_rejection():
    row = _interval(0)
    incomplete = dict(row.candidate_nonfocal_actions)
    incomplete.pop(99)
    malformed = c3.ForecastInterval(
        **{**row.__dict__, "candidate_nonfocal_actions": incomplete}
    )
    result = c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=[malformed, _interval(1), _interval(2)],
        focal_user_id=0,
    )
    assert not result.hard_safe
    assert not result.joint
    assert any("malformed_hard_safe_input" in reason for reason in result.reasons)


def test_declared_service_requires_the_focal_user_in_the_served_set():
    row = _interval(0)
    malformed = c3.ForecastInterval(
        **{
            **row.__dict__,
            "reference_served_users": tuple(range(1, 100)),
            "candidate_served_users": tuple(range(1, 100)),
        }
    )
    result = c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=[malformed, _interval(1), _interval(2)],
        focal_user_id=0,
    )
    assert not result.hard_safe
    assert any("focal_missing_from_served_set" in reason for reason in result.reasons)


def test_positive_eligible_load_keys_must_equal_declared_active_beams():
    def two_beam_power(total: float) -> object:
        fixed = 2 * 0.338 + 0.200
        return c3.PowerSnapshot(
            supply_power_w_by_beam={
                SOURCE: (total - fixed) / 2,
                DESTINATION: (total - fixed) / 2,
            },
            radiating_beams_by_satellite={8: 2},
            reported_fixed_power_w=fixed,
            reported_system_power_w=total,
            pa_identity_residual_w=0.0,
        )

    row = _interval(0)
    malformed = c3.ForecastInterval(
        **{
            **row.__dict__,
            "reference_power": two_beam_power(10.0),
            "candidate_power": two_beam_power(9.0),
            "reference_active_beams": (SOURCE, DESTINATION),
            "candidate_active_beams": (SOURCE, DESTINATION),
            "reference_active_satellites": (8,),
            "candidate_active_satellites": (8,),
        }
    )
    result = c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=[malformed, _interval(1), _interval(2)],
        focal_user_id=0,
    )
    assert not result.strict_load
    assert any("load_active_beam_mismatch" in reason for reason in result.reasons)


def test_eligible_load_sum_and_focal_inclusion_must_match_served_users():
    row = _interval(0)
    reference_loads = dict(row.reference_loads)
    reference_loads[(9, 1)] -= 1
    candidate_loads = c3.expected_candidate_loads(
        reference_loads,
        source_id=SOURCE,
        destination_id=DESTINATION,
    )
    malformed = c3.ForecastInterval(
        **{
            **row.__dict__,
            "reference_loads": reference_loads,
            "candidate_loads": candidate_loads,
            "reference_r3_total": c3.canonical_r3_total(reference_loads),
            "candidate_r3_total": c3.canonical_r3_total(candidate_loads),
        }
    )
    result = c3.certify_candidate(
        source_id=SOURCE,
        candidate_id=DESTINATION,
        intervals=[malformed, _interval(1), _interval(2)],
        focal_user_id=0,
    )
    assert not result.strict_load
    assert any("load_served_count_mismatch" in reason for reason in result.reasons)


def test_wrong_candidate_load_map_fails_load_but_keeps_power_layer_separate():
    wrong = {SOURCE: 2, DESTINATION: 3, (9, 1): 2}
    result = _certificate(candidate_loads=wrong)
    assert result.hard_safe
    assert not result.strict_load
    assert result.persistent_power
    assert not result.joint
    assert any("candidate_load_map_mismatch" in reason for reason in result.reasons)
    assert c3.support_waterfall([result]) == {
        "candidates": 1,
        "hard_safe": 1,
        "strict_load": 0,
        "persistent_power": 1,
        "joint": 0,
        "load_only": 0,
        "power_only": 1,
        "sign_disagreement": 1,
    }


def test_power_increase_does_not_erase_valid_strict_load_support():
    result = _certificate(candidate_power=10.5)
    assert result.hard_safe
    assert result.strict_load
    assert not result.persistent_power
    assert not result.joint
    waterfall = c3.support_waterfall([result])
    assert waterfall["load_only"] == 1
    assert waterfall["sign_disagreement"] == 1


def test_malformed_power_retains_three_failed_slots_and_remains_countable():
    result = _certificate(pa_residual=float("nan"))
    assert result.hard_safe
    assert result.strict_load
    assert not result.persistent_power
    assert not result.joint
    assert result.power_delta_w == (None, None, None)
    waterfall = c3.support_waterfall([result])
    assert waterfall["load_only"] == 1


def test_hard_safe_failure_blocks_all_nested_support():
    result = _certificate(nonfocal_match=False)
    assert not result.hard_safe
    assert not result.strict_load
    assert not result.persistent_power
    assert not result.joint
    assert any("nonfocal_action_mismatch" in reason for reason in result.reasons)


def _evidence(
    physical_id: tuple[int, int],
    *,
    gap: int,
    power: float,
    joint: bool = True,
) -> object:
    return c3.CandidateEvidence(
        candidate_id=physical_id,
        hard_safe=True,
        strict_load=True,
        persistent_power=joint,
        joint=joint,
        reasons=(),
        load_gap_score=gap,
        power_relief_j=power,
        intervals=(),
    )


def test_c3_gap_ranking_is_load_then_power_then_physical_id():
    rows = [
        _evidence((8, 4), gap=8, power=30.0),
        _evidence((8, 3), gap=9, power=20.0),
        _evidence((8, 2), gap=9, power=20.0),
        _evidence((8, 1), gap=100, power=100.0, joint=False),
    ]
    assert c3.select_c3_gap(rows).candidate_id == (8, 2)


def test_random_controls_draw_only_from_the_declared_layer():
    rows = [
        _evidence((8, 2), gap=9, power=20.0),
        _evidence((8, 3), gap=8, power=10.0),
    ]
    context = {
        "checkpoint_sha256": "c" * 64,
        "evaluation_seed": 7,
        "step_index": 2,
        "focal_user_id": 0,
    }
    first = c3.select_uniform(rows, layer="joint", **context)
    second = c3.select_uniform(rows, layer="joint", **context)
    assert first in rows
    assert second == first
    with pytest.raises(ValueError, match="unknown"):
        c3.select_uniform(rows, layer="power", **context)


def test_support_and_ranking_reject_malformed_or_non_nested_evidence():
    valid = _evidence((8, 2), gap=9, power=20.0)
    malformed_id = c3.CandidateEvidence(
        **{**valid.__dict__, "candidate_id": (8.0, 3)}
    )
    with pytest.raises(ValueError, match="physical ID"):
        c3.select_c3_gap([malformed_id])

    inconsistent = c3.CandidateEvidence(
        **{**valid.__dict__, "strict_load": False, "joint": True}
    )
    with pytest.raises(ValueError, match="nested"):
        c3.support_waterfall([inconsistent])

    with pytest.raises(ValueError, match="duplicate"):
        c3.support_waterfall([valid, valid])


def test_domain_seed_has_a_fixed_vector_and_forecast_realised_separation():
    checkpoint = "a" * 64
    forecast_seed = c3.derive_domain_seed(
        "SMC-ER-C3-FORECAST-v2", checkpoint, 17, 3, 4
    )
    assert forecast_seed == 2712096727728858561117115651041678626
    realised_seed = c3.derive_domain_seed(
        "SMC-ER-C3-REALISED-v2", checkpoint, 17, 3, 4
    )
    assert forecast_seed != realised_seed


def test_forecast_rngs_share_values_but_never_object_or_mutable_state():
    arguments = ("SMC-ER-C3-FORECAST-v2", "b" * 64, 9, 2, 7)
    left = c3.make_domain_rng(*arguments)
    right = c3.make_domain_rng(*arguments)
    assert left is not right
    assert left.bit_generator is not right.bit_generator
    assert np.array_equal(left.integers(0, 2**31, size=8), right.integers(0, 2**31, size=8))
    left.integers(0, 2**31, size=5)
    assert left.bit_generator.state != right.bit_generator.state


def test_rng_derivation_rejects_malformed_authority_or_indices():
    with pytest.raises(ValueError, match="SHA-256"):
        c3.derive_domain_seed("SMC-ER-C3-FORECAST-v2", "not-a-hash", 1, 2, 3)
    with pytest.raises(ValueError, match="exact integer"):
        c3.derive_domain_seed("SMC-ER-C3-FORECAST-v2", "a" * 64, True, 2, 3)


def test_option_state_moves_holds_then_releases_to_main():
    state = c3.OptionState.start(DESTINATION)
    steps = []
    for interval in range(4):
        step, state = c3.advance_option(
            state,
            interval=interval,
            hold_valid=True,
            service_feasible=True,
            episode_done=False,
        )
        steps.append(step)
    assert [step.focal_action for step in steps] == [
        DESTINATION,
        DESTINATION,
        DESTINATION,
        None,
    ]
    assert [step.event for step in steps] == [
        c3.EventClass.PHI1,
        c3.EventClass.NONE,
        c3.EventClass.NONE,
        c3.EventClass.NONE,
    ]
    assert [step.main_controls for step in steps] == [False, False, False, True]
    assert state.phase is c3.OptionPhase.RELEASED


def test_option_invalidity_terminates_explicitly_without_hidden_substitute():
    state = c3.OptionState.start(DESTINATION)
    _, state = c3.advance_option(
        state,
        interval=0,
        hold_valid=True,
        service_feasible=True,
        episode_done=False,
    )
    failed, state = c3.advance_option(
        state,
        interval=1,
        hold_valid=False,
        service_feasible=True,
        episode_done=False,
    )
    assert failed.focal_action is None
    assert failed.termination_reason == "invalid_hold"
    assert not failed.main_controls
    assert state.phase is c3.OptionPhase.TERMINATED

    resumed, state = c3.advance_option(
        state,
        interval=2,
        hold_valid=True,
        service_feasible=True,
        episode_done=False,
    )
    assert resumed.focal_action is None
    assert resumed.main_controls
    assert state.phase is c3.OptionPhase.TERMINATED


def test_option_state_rejects_manual_malformed_state_and_out_of_order_steps():
    malformed = c3.OptionState((8.0, 2), c3.OptionPhase.FORCED, 0)
    with pytest.raises(ValueError, match="physical ID"):
        c3.advance_option(
            malformed,
            interval=0,
            hold_valid=True,
            service_feasible=True,
            episode_done=False,
        )
    with pytest.raises(ValueError, match="sequentially"):
        c3.advance_option(
            c3.OptionState.start(DESTINATION),
            interval=1,
            hold_valid=True,
            service_feasible=True,
            episode_done=False,
        )


def _branches(
    *,
    ref_extended: float = -100.0,
    cert_extended: float = -95.0,
    gap_extended: float = -90.0,
    ref_episode: float = -300.0,
    cert_episode: float = -290.0,
    gap_episode: float = -280.0,
    power: tuple[float, ...] = (1.0, 0.5, 0.25),
    service: float = 1.0,
    focal_user_id: int = 0,
    trace_intervals: int = 4,
) -> dict[str, object]:
    trace = tuple(
        {
            user: SOURCE
            for user in range(100)
            if user != focal_user_id
        }
        for _ in range(trace_intervals)
    )

    def outcome(
        name: str,
        extended: float,
        episode: float,
        totals: tuple[float, float, float],
        *,
        served_fraction: float = 1.0,
    ) -> object:
        events = [c3.EventClass.NONE] * trace_intervals
        if name != "reference":
            events[0] = c3.EventClass.PHI1
        return c3.BranchOutcome(
            name=name,
            r3_extended=extended,
            r3_episode=episode,
            forced_power=tuple(_power_with_total(total) for total in totals),
            focal_service_by_interval=(True,) * trace_intervals,
            served_fraction=served_fraction,
            nonfocal_actions_by_interval=trace,
            event_classes_by_interval=tuple(events),
        )

    return {
        "reference": outcome(
            "reference", ref_extended, ref_episode, (10.0, 10.0, 10.0)
        ),
        "C3-SAFE-R": outcome(
            "C3-SAFE-R", -98.0, -296.0, (9.8, 9.8, 9.8)
        ),
        "C3-LOAD-R": outcome(
            "C3-LOAD-R", -96.0, -292.0, (9.7, 9.7, 9.7)
        ),
        "C3-CERT-R": outcome(
            "C3-CERT-R", cert_extended, cert_episode, (9.5, 9.5, 9.5)
        ),
        "C3-GAP": outcome(
            "C3-GAP",
            gap_extended,
            gap_episode,
            tuple(10.0 - value for value in power),
            served_fraction=service,
        ),
    }


def test_paired_effects_use_extended_and_episode_canonical_r3():
    effects = c3.paired_effects(_branches())
    assert effects["Delta_R3_ref_extended"] == 10.0
    assert effects["Delta_R3_cert_extended"] == 5.0
    assert effects["Delta_R3_ref_episode"] == 20.0
    assert effects["Delta_R3_cert_episode"] == 10.0
    assert effects["realised_power_guard"] is True
    assert effects["focal_service_preserved"] is True
    assert effects["nonfocal_causality_guard"] is True


def test_paired_effects_requires_exact_five_arm_shape():
    branches = _branches()
    branches.pop("C3-SAFE-R")
    with pytest.raises(ValueError, match="exact five-arm"):
        c3.paired_effects(branches)


def _passing_rows() -> list[dict[str, object]]:
    effects = c3.paired_effects(_branches())
    return [
        {
            "evaluation_seed": index % 5,
            "anchor_id": f"anchor-{index}",
            **effects,
        }
        for index in range(20)
    ]


def test_aggregation_weights_anchors_and_seed_directions_explicitly():
    rows = _passing_rows()
    aggregate = c3.aggregate_effects(rows)
    assert aggregate["eligible_anchors"] == 20
    assert set(aggregate["support_by_seed"].values()) == {4}
    assert aggregate["pooled_mean"]["Delta_R3_cert_episode"] == 10.0
    assert aggregate["positive_seed_count"]["Delta_R3_cert_episode"] == 5


def test_terminal_rule_passes_only_both_primary_controls_and_both_windows():
    rows = _passing_rows()
    aggregate = c3.aggregate_effects(rows)
    assert c3.stage0_decision(rows, aggregate, engineering_ok=True) == c3.PASS_RESULT

    broken = [dict(row) for row in rows]
    for row in broken:
        row["Delta_R3_cert_extended"] = 0.0
    assert (
        c3.stage0_decision(
            broken,
            c3.aggregate_effects(broken),
            engineering_ok=True,
        )
        == c3.DROP_ROLE
    )


def test_terminal_rule_recomputes_and_rejects_a_forged_aggregate():
    rows = _passing_rows()
    forged = c3.aggregate_effects(rows)
    forged["pooled_mean"]["Delta_R3_ref_extended"] = 999.0
    assert (
        c3.stage0_decision(rows, forged, engineering_ok=True)
        == c3.CERTIFICATE_FAILURE
    )


def test_nonfinite_effect_row_fails_closed_as_certificate_failure():
    rows = _passing_rows()
    rows[0]["Delta_R3_ref_extended"] = float("nan")
    assert (
        c3.stage0_decision(rows, {}, engineering_ok=True)
        == c3.CERTIFICATE_FAILURE
    )


def test_effect_rows_require_the_supporting_arm_contrasts():
    rows = _passing_rows()
    rows[0].pop("Delta_R3_load_safe_extended")
    with pytest.raises(ValueError, match="supporting"):
        c3.aggregate_effects(rows)
    assert (
        c3.stage0_decision(rows, {}, engineering_ok=True)
        == c3.CERTIFICATE_FAILURE
    )


def test_terminal_rule_requires_support_power_service_and_engineering_guards():
    rows = _passing_rows()
    short = rows[:-1]
    assert (
        c3.stage0_decision(
            short,
            c3.aggregate_effects(short),
            engineering_ok=True,
        )
        == c3.DROP_ROLE
    )

    bad_power = [dict(row) for row in rows]
    bad_power[0]["realised_power_guard"] = False
    assert (
        c3.stage0_decision(
            bad_power,
            c3.aggregate_effects(bad_power),
            engineering_ok=True,
        )
        == c3.DROP_ROLE
    )

    bad_service = [dict(row) for row in rows]
    for row in bad_service:
        row["service_delta_ref"] = -0.006
    assert (
        c3.stage0_decision(
            bad_service,
            c3.aggregate_effects(bad_service),
            engineering_ok=True,
        )
        == c3.DROP_ROLE
    )

    assert (
        c3.stage0_decision(rows, c3.aggregate_effects(rows), engineering_ok=False)
        == c3.CERTIFICATE_FAILURE
    )


def _engineering_guards() -> dict[str, bool]:
    return {name: True for name in c3.REQUIRED_ENGINEERING_GUARDS}


def _anchors() -> list[object]:
    waterfall = {
        "candidates": 3,
        "hard_safe": 3,
        "strict_load": 2,
        "persistent_power": 2,
        "joint": 1,
        "load_only": 1,
        "power_only": 1,
        "sign_disagreement": 2,
    }
    return [
        c3.AnchorOutcome(
            evaluation_seed=index % 5,
            step_index=index % 7,
            focal_user_id=index % 100,
            anchor_id=f"anchor-{index}",
            anchor_fingerprint_sha256=f"{index + 1:064x}",
            support_waterfall=waterfall,
            branches=_branches(
                focal_user_id=index % 100,
                trace_intervals=10 - (index % 7),
            ),
        )
        for index in range(20)
    ]


def test_receipt_contains_exact_five_arms_named_guards_and_internal_aggregate():
    receipt = c3.build_stage0_receipt(_anchors(), _engineering_guards())
    assert receipt.arm_names == c3.REQUIRED_ARMS
    assert receipt.decision == c3.PASS_RESULT
    assert receipt.aggregate == c3.aggregate_effects(receipt.paired_rows)
    ledger = {entry.name: entry.passed for entry in receipt.guard_ledger}
    assert all(ledger.values())
    assert ledger["five_arm_receipt"]
    assert ledger["aggregate_recomputed"]


def test_receipt_missing_arm_or_named_guard_is_certificate_failure():
    anchors = _anchors()
    first = anchors[0]
    branches = dict(first.branches)
    branches.pop("C3-LOAD-R")
    anchors[0] = c3.AnchorOutcome(
        evaluation_seed=first.evaluation_seed,
        step_index=first.step_index,
        focal_user_id=first.focal_user_id,
        anchor_id=first.anchor_id,
        anchor_fingerprint_sha256=first.anchor_fingerprint_sha256,
        support_waterfall=first.support_waterfall,
        branches=branches,
    )
    assert (
        c3.build_stage0_receipt(anchors, _engineering_guards()).decision
        == c3.CERTIFICATE_FAILURE
    )

    guards = _engineering_guards()
    guards.pop("rng_independence")
    assert (
        c3.build_stage0_receipt(_anchors(), guards).decision
        == c3.CERTIFICATE_FAILURE
    )


def test_receipt_requires_causal_trace_through_episode_end():
    anchors = _anchors()
    first = anchors[0]
    anchors[0] = c3.AnchorOutcome(
        evaluation_seed=first.evaluation_seed,
        step_index=first.step_index,
        focal_user_id=first.focal_user_id,
        anchor_id=first.anchor_id,
        anchor_fingerprint_sha256=first.anchor_fingerprint_sha256,
        support_waterfall=first.support_waterfall,
        branches=_branches(focal_user_id=first.focal_user_id, trace_intervals=4),
    )
    assert (
        c3.build_stage0_receipt(anchors, _engineering_guards()).decision
        == c3.CERTIFICATE_FAILURE
    )


def test_receipt_rejects_malformed_realised_event_timing():
    anchors = _anchors()
    first = anchors[0]
    branches = dict(first.branches)
    gap = branches["C3-GAP"]
    events = list(gap.event_classes_by_interval)
    events[0] = c3.EventClass.PHI2
    branches["C3-GAP"] = c3.BranchOutcome(
        **{**gap.__dict__, "event_classes_by_interval": tuple(events)}
    )
    anchors[0] = c3.AnchorOutcome(
        evaluation_seed=first.evaluation_seed,
        step_index=first.step_index,
        focal_user_id=first.focal_user_id,
        anchor_id=first.anchor_id,
        anchor_fingerprint_sha256=first.anchor_fingerprint_sha256,
        support_waterfall=first.support_waterfall,
        branches=branches,
    )
    assert (
        c3.build_stage0_receipt(anchors, _engineering_guards()).decision
        == c3.CERTIFICATE_FAILURE
    )


def test_well_formed_adverse_power_is_a_named_drop_guard_not_engineering_failure():
    anchors = _anchors()
    first = anchors[0]
    anchors[0] = c3.AnchorOutcome(
        evaluation_seed=first.evaluation_seed,
        step_index=first.step_index,
        focal_user_id=first.focal_user_id,
        anchor_id=first.anchor_id,
        anchor_fingerprint_sha256=first.anchor_fingerprint_sha256,
        support_waterfall=first.support_waterfall,
        branches=_branches(
            power=(-0.1, 0.5, 0.25),
            focal_user_id=first.focal_user_id,
            trace_intervals=10 - first.step_index,
        ),
    )
    receipt = c3.build_stage0_receipt(anchors, _engineering_guards())
    assert receipt.decision == c3.DROP_ROLE
    ledger = {entry.name: entry.passed for entry in receipt.guard_ledger}
    assert ledger["realised_power_guard"] is False
    assert ledger["five_arm_receipt"] is True
