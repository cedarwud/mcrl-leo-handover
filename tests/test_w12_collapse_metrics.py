"""W-12 / G-3 — the four collapse indicators.

G-3 fails on a MISSING indicator, not on a bad value, because the documented
error is reporting two of the four and concluding the collapse was fixed.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.collapse_metrics import (
    REQUIRED_G3_FIELDS,
    assert_g3_complete,
    compute_collapse_metrics,
)

USERS, ACTIONS = 100, 28


def _all_valid():
    return np.ones((USERS, ACTIONS), dtype=bool)


def _collapsed(rng, scale=1.0):
    """One action dominates for everybody."""
    q = rng.normal(0.0, 0.01 * scale, (USERS, ACTIONS))
    q[:, 3] += 1.0 * scale
    return q


def _dispersed(rng, scale=1.0):
    q = rng.normal(0.0, scale, (USERS, ACTIONS))
    return q


# -- completeness is the gate ---------------------------------------------


def test_all_four_indicators_are_required():
    assert REQUIRED_G3_FIELDS == (
        "active_beam_count",
        "argmax_agreement",
        "q_margin",
        "q_entropy",
    )


def test_a_partial_report_is_refused():
    """Exactly the two-of-four error the ablation fell into."""
    with pytest.raises(MCRLContractError, match="missing"):
        assert_g3_complete(
            {"active_beam_count": 4.39, "argmax_agreement": 0.484}
        )


@pytest.mark.parametrize("dropped", REQUIRED_G3_FIELDS)
def test_dropping_any_single_indicator_fails(dropped):
    report = {field: 1.0 for field in REQUIRED_G3_FIELDS}
    del report[dropped]
    with pytest.raises(MCRLContractError, match=dropped):
        assert_g3_complete(report)


def test_a_complete_report_passes_and_round_trips():
    report = {field: 0.5 for field in REQUIRED_G3_FIELDS}
    assert assert_g3_complete(report) == report


def test_non_finite_indicators_are_refused():
    report = {field: 1.0 for field in REQUIRED_G3_FIELDS}
    report["q_margin"] = float("nan")
    with pytest.raises(MCRLContractError, match="finite"):
        assert_g3_complete(report)


def test_the_computed_metrics_always_carry_all_four():
    rng = np.random.default_rng(0)
    q = _collapsed(rng)
    metrics = compute_collapse_metrics(q, _all_valid(), q.argmax(axis=1))
    assert_g3_complete(metrics.as_dict())
    rendered = metrics.format_report()
    for field in REQUIRED_G3_FIELDS:
        assert field in rendered


# -- the indicators actually discriminate ---------------------------------


def test_a_collapsed_policy_shows_one_beam_and_full_agreement():
    rng = np.random.default_rng(1)
    q = _collapsed(rng)
    metrics = compute_collapse_metrics(q, _all_valid(), q.argmax(axis=1))
    assert metrics.active_beam_count == 1.0
    assert metrics.argmax_agreement == 1.0


def test_a_dispersed_policy_shows_many_beams_and_low_agreement():
    rng = np.random.default_rng(2)
    q = _dispersed(rng)
    metrics = compute_collapse_metrics(q, _all_valid(), q.argmax(axis=1))
    assert metrics.active_beam_count > 20
    assert metrics.argmax_agreement < 0.15


# -- ★ why the margin must be normalised ----------------------------------


def test_the_raw_margin_moves_with_the_q_scale_and_the_normalised_one_does_not():
    """The confound the normalisation removes, demonstrated.

    Two policies that differ ONLY by a uniform rescaling of Q have identical
    discrimination.  The raw margin says one is 100x better; the normalised
    margin correctly says they are the same.
    """
    rng = np.random.default_rng(3)
    base = _dispersed(np.random.default_rng(3))
    scaled = base * 0.01

    big = compute_collapse_metrics(base, _all_valid(), base.argmax(axis=1))
    small = compute_collapse_metrics(scaled, _all_valid(), scaled.argmax(axis=1))

    assert small.q_margin_raw == pytest.approx(big.q_margin_raw * 0.01, rel=1e-9)
    assert small.q_margin == pytest.approx(big.q_margin, rel=1e-9)
    del rng


def test_the_normalised_margin_responds_to_shape_not_scale():
    """It moves when the Q distribution genuinely flattens."""
    rng = np.random.default_rng(4)
    peaked = _collapsed(rng)
    flat = _dispersed(np.random.default_rng(4))

    peaked_metrics = compute_collapse_metrics(
        peaked, _all_valid(), peaked.argmax(axis=1)
    )
    flat_metrics = compute_collapse_metrics(flat, _all_valid(), flat.argmax(axis=1))
    assert peaked_metrics.q_margin > 5.0 * flat_metrics.q_margin


def test_the_first_two_indicators_alone_would_call_a_flat_policy_healthy():
    """The exact misreading G-3 exists to prevent.

    A near-flat Q with dispersed argmax looks de-collapsed on beams and
    agreement, and is only distinguishable by looking at the margin against
    a genuinely discriminative policy of the same scale.
    """
    rng = np.random.default_rng(5)
    flat = rng.normal(0.0, 1e-4, (USERS, ACTIONS))
    metrics = compute_collapse_metrics(flat, _all_valid(), flat.argmax(axis=1))

    # On the first two, it looks fine.
    assert metrics.active_beam_count > 20
    assert metrics.argmax_agreement < 0.15
    # The scale it is operating at is what the raw margin exposes.
    assert metrics.q_margin_raw < 1e-3
    assert metrics.q_range < 1e-3


def test_the_range_used_for_normalisation_is_reported():
    """So the normalisation itself can be audited rather than trusted."""
    rng = np.random.default_rng(6)
    q = _dispersed(rng)
    metrics = compute_collapse_metrics(q, _all_valid(), q.argmax(axis=1))
    assert metrics.q_range > 0.0
    ordered = np.sort(q, axis=1)[:, ::-1]
    per_user = (ordered[:, 0] - ordered[:, 1]) / (
        ordered[:, 0] - ordered[:, -1]
    )
    assert metrics.q_margin == pytest.approx(float(np.mean(per_user)))
    assert "q_range" in metrics.as_dict()


def test_normalised_margin_is_averaged_per_user_not_as_a_ratio_of_means():
    """Heterogeneous Q scales must not let one user dominate the normaliser.

    User 0 has a 1/100 relative margin and user 1 has a 1/1 relative
    margin.  The frozen wording is per-user normalisation, so the aggregate
    is mean([0.01, 1.0]) = 0.505.  Dividing the two population means would
    instead return 1/50.5 and silently reweight users by their Q range.
    """
    q = np.array(
        [
            [100.0, 99.0, 0.0],
            [1.0, 0.0, 0.0],
        ]
    )
    metrics = compute_collapse_metrics(
        q,
        np.ones_like(q, dtype=bool),
        np.array([0, 0]),
    )

    assert metrics.q_margin == pytest.approx(0.505)
    assert metrics.q_margin_raw == pytest.approx(1.0)
    assert metrics.q_range == pytest.approx(50.5)


def test_legacy_active_beam_name_exposes_its_action_slot_semantics():
    q = np.array([[2.0, 1.0], [1.0, 2.0]])
    metrics = compute_collapse_metrics(
        q,
        np.ones_like(q, dtype=bool),
        np.array([0, 1]),
    )

    assert metrics.active_action_slot_count == metrics.active_beam_count == 2.0
    assert "distinct_action_slots" in metrics.format_report()


# -- entropy ---------------------------------------------------------------


def test_entropy_is_normalised_into_the_unit_interval():
    rng = np.random.default_rng(7)
    for builder in (_collapsed, _dispersed):
        q = builder(rng)
        metrics = compute_collapse_metrics(q, _all_valid(), q.argmax(axis=1))
        assert 0.0 <= metrics.q_entropy <= 1.0


def test_a_hugely_peaked_row_has_near_zero_entropy():
    q = np.zeros((1, ACTIONS))
    q[0, 5] = 500.0
    metrics = compute_collapse_metrics(q, np.ones((1, ACTIONS), bool), np.array([5]))
    assert metrics.q_entropy == pytest.approx(0.0, abs=1e-6)


def test_a_tied_row_has_maximal_entropy():
    q = np.zeros((1, ACTIONS))
    metrics = compute_collapse_metrics(q, np.ones((1, ACTIONS), bool), np.array([0]))
    assert metrics.q_entropy == pytest.approx(1.0)
    assert metrics.q_margin == 0.0


def test_entropy_alone_did_not_separate_the_arms_in_the_source_ablation():
    """SDD §2.3 records ``q_entropy ≈ 1.0`` for BOTH learning rates.

    Reproduced here: with Q values of order 1 over 28 actions the softmax is
    still nearly uniform, so entropy is a weak separator.  That is precisely
    why G-3 demands four indicators rather than picking a favourite.
    """
    rng = np.random.default_rng(8)
    collapsed = compute_collapse_metrics(
        _collapsed(rng), _all_valid(), _collapsed(np.random.default_rng(8)).argmax(1)
    )
    assert collapsed.q_entropy > 0.9


# -- masks and no-ops ------------------------------------------------------


def test_masked_actions_are_excluded_from_the_margin():
    q = np.zeros((1, ACTIONS))
    q[0, 0] = 10.0  # best, but masked out
    q[0, 1] = 5.0
    q[0, 2] = 1.0
    mask = np.ones((1, ACTIONS), dtype=bool)
    mask[0, 0] = False
    metrics = compute_collapse_metrics(q, mask, np.array([1]))
    assert metrics.q_margin_raw == pytest.approx(4.0)


def test_unserved_users_do_not_count_toward_beams_or_agreement():
    rng = np.random.default_rng(9)
    q = _dispersed(rng)
    actions = q.argmax(axis=1)
    actions[:50] = -1  # half the population unserved
    metrics = compute_collapse_metrics(q, _all_valid(), actions)
    assert metrics.active_beam_count <= 50
    assert 0.0 < metrics.argmax_agreement <= 1.0


def test_an_all_unserved_step_reports_zeros_rather_than_dividing_by_zero():
    q = np.zeros((4, ACTIONS))
    metrics = compute_collapse_metrics(
        q, _all_valid()[:4], np.full(4, -1, dtype=np.int64)
    )
    assert metrics.active_beam_count == 0.0
    assert metrics.argmax_agreement == 0.0
    assert_g3_complete(metrics.as_dict())


def test_a_single_candidate_row_is_skipped_rather_than_claiming_certainty():
    mask = np.zeros((2, ACTIONS), dtype=bool)
    mask[0, :2] = True
    mask[1, 0] = True  # only one candidate
    q = np.zeros((2, ACTIONS))
    q[0, 0] = 1.0
    metrics = compute_collapse_metrics(q, mask, np.array([0, 0]))
    assert metrics.q_margin_raw == pytest.approx(1.0)


def test_shape_and_finiteness_violations_fail_loud():
    with pytest.raises(MCRLContractError, match=r"\(U, A\)"):
        compute_collapse_metrics(
            np.zeros((2, 3)), np.ones((2, 4), bool), np.zeros(2, dtype=np.int64)
        )
    with pytest.raises(MCRLContractError, match="selected_actions"):
        compute_collapse_metrics(
            np.zeros((2, 3)), np.ones((2, 3), bool), np.zeros(3, dtype=np.int64)
        )
    with pytest.raises(MCRLContractError, match="finite"):
        compute_collapse_metrics(
            np.full((1, 2), np.nan), np.ones((1, 2), bool), np.array([0])
        )


# ---------------------------------------------------------------------------
# W-28: the four must reach EpisodeLog, or the run cannot answer B17 Q1
# ---------------------------------------------------------------------------


def test_the_episode_log_carries_all_four_collapse_indicators():
    """G-3 fails on a MISSING indicator, and B17 Q1 is the go/no-go.

    ``collapse_metrics.py`` existed with zero callers in the training loop
    until 2026-08-23, so a 9,000-episode run would have finished unable to
    say whether shared-Q + argmax collapsed — and the fix costs a re-run.
    """
    from mcrl.runtime.trainer_spec import EpisodeLog

    from mcrl.runtime.trainer_spec import CollapseSample

    sample_fields = set(CollapseSample.__dataclass_fields__)
    assert set(REQUIRED_G3_FIELDS) <= sample_fields, sorted(
        set(REQUIRED_G3_FIELDS) - sample_fields
    )
    # The raw gap and its divisor travel too, so the scale stays auditable.
    assert {"q_margin_raw", "q_range"} <= sample_fields
    # And the executed pair, kept apart from the greedy one it must not be
    # confused with: epsilon is live at every step, first included.
    assert {
        "active_beam_count_executed",
        "argmax_agreement_executed",
    } <= sample_fields
    # Both ends of the episode, because collapse develops within one.
    fields = set(EpisodeLog.__dataclass_fields__)
    assert {"collapse_first", "collapse_last"} <= fields
    # And both reward scalings, for B17 Q2's effective trade-off.
    assert {
        "r1_mean_calibrated",
        "r2_mean_calibrated",
        "r3_mean_calibrated",
    } <= fields


def test_the_episode_log_report_satisfies_the_g3_gate():
    """The log's own report must pass ``assert_g3_complete`` unchanged."""
    from mcrl.runtime.trainer_spec import EpisodeLog

    from mcrl.runtime.trainer_spec import CollapseSample

    def sample(beams, agreement):
        return CollapseSample(
            q_margin=0.1, q_entropy=0.9, q_margin_raw=1.0, q_range=10.0,
            active_beam_count=beams, argmax_agreement=agreement,
            active_beam_count_executed=beams + 3.0,
            argmax_agreement_executed=agreement / 2.0,
        )

    log = EpisodeLog(
        episode=0, epsilon=1.0, r1_mean=1.0, r2_mean=0.0, r3_mean=-1.0,
        scalar_reward=0.0, total_handovers=0, replay_size=0,
        collapse_first=sample(7.0, 0.25),
        collapse_last=sample(3.0, 0.60),
    )
    for point in ("first", "last"):
        report = log.collapse_report(point)
        assert assert_g3_complete(report) == report

    # The DIFFERENCE is the signal: this episode ended on fewer beams with
    # more agreement than it started, which is what collapse looks like.
    drift = log.collapse_drift()
    assert drift["active_beam_count"] == -4.0
    assert drift["argmax_agreement"] == pytest.approx(0.35)


def test_a_log_missing_an_indicator_still_fails_the_gate():
    """The gate has to keep its teeth now that the fields exist."""
    from mcrl.runtime.trainer_spec import EpisodeLog

    from mcrl.runtime.trainer_spec import CollapseSample

    log = EpisodeLog(
        episode=0, epsilon=1.0, r1_mean=0.0, r2_mean=0.0, r3_mean=0.0,
        scalar_reward=0.0, total_handovers=0, replay_size=0,
        collapse_first=CollapseSample(0.1, 0.9, 1.0, 10.0, 7.0, 0.2, 7.0, 0.2),
        collapse_last=CollapseSample(0.1, 0.9, 1.0, 10.0, 7.0, 0.2, 7.0, 0.2),
    )
    partial = {
        k: v for k, v in log.collapse_report().items() if k != "q_entropy"
    }
    with pytest.raises(MCRLContractError, match="q_entropy"):
        assert_g3_complete(partial)


def test_an_absent_sample_fails_loudly_rather_than_reporting_zeros():
    """Zeros would let a run report "no collapse" having measured nothing."""
    from mcrl.runtime.trainer_spec import EpisodeLog

    log = EpisodeLog(
        episode=11, epsilon=0.5, r1_mean=0.0, r2_mean=0.0, r3_mean=0.0,
        scalar_reward=0.0, total_handovers=0, replay_size=0,
    )
    with pytest.raises(ValueError, match="no last-step collapse sample"):
        log.collapse_report()
    with pytest.raises(ValueError, match="no first-step collapse sample"):
        log.collapse_report("first")
