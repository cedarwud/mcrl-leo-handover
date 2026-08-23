"""W-27 — probes P2, P4, P5, P7 and the harness they share.

The harness exists because four of the seven probes are ablation-shaped and
each would carry the same stream defect independently.  Putting the gate
and the generators in one place is the structural version of the ruling's
warning that converging the scripts is where three generators quietly
become one.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.antenna import RX_ENVELOPE_MIN_DEG
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.dwell import DwellConfig
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import (
    RANDOM_MASKED,
    STAY_IF_POSSIBLE,
    build_reference_policy,
)
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError
from mcrl.runtime.probe_harness import ProbeStreams, assert_probe_is_frozen, drive
from mcrl.runtime.probe_p2 import run_probe_p2
from mcrl.runtime.probe_p4 import run_probe_p4
from mcrl.runtime.probe_p5 import run_probe_p5
from mcrl.runtime.probe_p7 import run_probe_p7

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
USERS, SEED = 10, 4242
EPOCHS = [
    dt.datetime(2026, 8, 8, 0, 0, tzinfo=dt.timezone.utc) + dt.timedelta(hours=17 * k)
    for k in range(2)
]


def _env(physics=None, dwell_steps=None):
    kwargs = {"mobility": MobilityConfig(num_users=USERS)}
    if dwell_steps:
        kwargs["dwell"] = DwellConfig(steps=dwell_steps)
    return StepEnvironment(
        ScenarioDriver(TleArchive(_ARCHIVE), ScenarioConfig(**kwargs)),
        physics=physics or PhysicsConfig(),
    )


@pytest.fixture(scope="module")
def record():
    from mcrl.runtime.prereg_draft import freeze

    return freeze()


# -- the harness -----------------------------------------------------------


def test_the_three_streams_are_independent_and_seed_reproducible():
    """One seed in, three streams out, and none of them is the others."""
    first, second = ProbeStreams.spawn(SEED), ProbeStreams.spawn(SEED)
    assert first.env.random() == second.env.random()

    fresh = ProbeStreams.spawn(SEED)
    draws = {fresh.env.random(), fresh.mobility.random(), fresh.action.random()}
    assert len(draws) == 3, "two streams produced the same value"


def test_consuming_one_stream_does_not_move_the_others():
    """The whole point: a fading change must not re-draw the users.

    With one generator, advancing it for fading shifts every later mobility
    and warm-start draw, and the 'fading ablation' measures fading plus a
    different sample — measured at 11 outages of difference on 2026-08-23.
    """
    untouched = ProbeStreams.spawn(SEED)
    baseline = (untouched.mobility.random(), untouched.action.random())

    drained = ProbeStreams.spawn(SEED)
    for _ in range(1000):
        drained.env.random()
    assert (drained.mobility.random(), drained.action.random()) == baseline


@requires_archive
def test_the_gate_refuses_a_probe_absent_from_the_frozen_grid(record):
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    with pytest.raises(MCRLContractError, match="no P99 entry"):
        assert_probe_is_frozen(record, "P99", policy)


@requires_archive
def test_the_gate_refuses_a_closing_probe_without_its_mapping(record):
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    with pytest.raises(MCRLContractError, match="must be in the frozen record"):
        assert_probe_is_frozen(
            record, "P4", policy, requires_mapping="Q-Z nonexistent"
        )


@requires_archive
def test_drive_yields_the_observation_the_actions_were_chosen_against(record):
    """Not the one that follows — that would be reading the future."""
    steps = list(
        drive(
            _env(),
            build_reference_policy(STAY_IF_POSSIBLE, seed=7),
            EPOCHS[:1],
            ProbeStreams.spawn(SEED),
        )
    )
    assert steps
    for observation, actions, outcome in steps:
        assert len(actions) == USERS
        # The action must be legal under THIS observation's mask.
        for uid, action in enumerate(actions.tolist()):
            if action >= 0:
                assert observation.masks[uid][action]
        assert outcome.observation is not observation


def test_drive_refuses_an_empty_epoch_list():
    with pytest.raises(MCRLContractError, match="at least one epoch"):
        list(drive(None, None, [], ProbeStreams.spawn(SEED)))


# -- P4 --------------------------------------------------------------------


@requires_archive
def test_p4_ablates_by_arithmetic_not_by_a_second_rollout(record):
    """A re-run would change the served set and confound the ablation."""
    result = run_probe_p4(
        prereg=record,
        policy=build_reference_policy(STAY_IF_POSSIBLE, seed=7),
        environment=_env(),
        epochs=EPOCHS,
        streams=ProbeStreams.spawn(SEED),
    )
    assert "not a second rollout" in result["ablation_method"]
    # Removing interference can only RAISE the SINR, never lower it.
    assert result["sinr_cost_of_interference_db"]["min"] >= -1e-9
    assert (
        result["sinr_db_without_co_colour_sum"]["p50"] >= result["sinr_db"]["p50"]
    )
    assert 0.0 <= result["intra_fraction_of_total"]["p50"] <= 1.0
    assert result["served_links"] > 0


# -- P5 --------------------------------------------------------------------


@requires_archive
def test_p5_reports_both_a_count_and_a_power_share(record):
    """One without the other cannot tell rare-and-dominant from rare-and-not."""
    result = run_probe_p5(
        prereg=record,
        policy=build_reference_policy(STAY_IF_POSSIBLE, seed=7),
        environment=_env(),
        epochs=EPOCHS,
        streams=ProbeStreams.spawn(SEED),
    )
    assert result["theta_r_min_deg"] == RX_ENVELOPE_MIN_DEG
    for key in (
        "fraction_of_evaluations_below_theta_r_min",
        "fraction_of_interference_power_below_theta_r_min",
    ):
        assert 0.0 <= result[key] <= 1.0
    # Co-satellite terms are excluded, not folded in: they sit at 0 deg by
    # P-10 and would manufacture a disclosure out of a modelling assumption.
    assert result["co_satellite_terms"] > 0
    assert result["separation_deg"]["min"] > 0.0
    # The power share is over CONTRIBUTING terms, a subset of cross-satellite.
    assert result["contributing_terms"] <= result["cross_satellite_terms"]
    assert "CO-COLOUR" in result["power_weighting_note"]


@requires_archive
def test_p5_refuses_a_record_whose_threshold_disagrees_with_the_code(record):
    from mcrl.runtime.prereg import PreregRecord

    section = dict(record.sections["antenna_and_link_budget"])
    section["rx_envelope_min_deg"] = 1.0
    tampered = PreregRecord(
        sections=dict(record.sections) | {"antenna_and_link_budget": section},
        holdout=record.holdout,
    ).with_digest()
    with pytest.raises(MCRLContractError, match="disagree"):
        run_probe_p5(
            prereg=tampered,
            policy=build_reference_policy(STAY_IF_POSSIBLE, seed=7),
            environment=_env(),
            epochs=EPOCHS,
            streams=ProbeStreams.spawn(SEED),
        )


# -- P7 --------------------------------------------------------------------


@requires_archive
def test_p7_reports_the_three_mask_terms_apart(record):
    """An AND cannot be attributed; "28/28 valid" names no culprit."""
    result = run_probe_p7(
        prereg=record,
        policy=build_reference_policy(RANDOM_MASKED, seed=7),
        environment=_env(),
        epochs=EPOCHS,
        streams=ProbeStreams.spawn(SEED),
    )
    for key in (
        "slots_killed_by_unoccupied_slot",
        "slots_killed_by_absent_cell",
        "slots_killed_by_unreachable_cell",
    ):
        assert key in result
    assert "OVERLAP" in result["term_attrition_note"]
    assert isinstance(result["mask_is_ever_binding"], bool)
    assert isinstance(result["power_gate_is_binding"], bool)
    assert result["segment_warm_start"] == "uniform-episode-length"


@requires_archive
def test_p7_separates_the_two_warm_start_arms(record):
    """They disagree about whether the power gate exists at all."""
    def run(physics):
        return run_probe_p7(
            prereg=record,
            policy=build_reference_policy(RANDOM_MASKED, seed=7),
            environment=_env(physics),
            epochs=EPOCHS,
            streams=ProbeStreams.spawn(SEED),
        )

    warm = run(PhysicsConfig())
    cold = run(PhysicsConfig(segment_warm_start="none"))
    assert warm["segment_warm_start"] != cold["segment_warm_start"]
    # The warm arm enters segments already partway through the budget.
    assert (
        warm["feasible_budget_fraction"]["p50"]
        >= cold["feasible_budget_fraction"]["p50"]
    )


# -- P2 --------------------------------------------------------------------


@requires_archive
def test_p2_gives_every_arm_identical_streams(record):
    """Otherwise the sweep measures N *and* a different sample."""
    result = run_probe_p2(
        prereg=record,
        policy_factory=lambda: build_reference_policy(STAY_IF_POSSIBLE, seed=7),
        environment_factory=lambda n: _env(dwell_steps=n),
        epochs=EPOCHS,
        seed=SEED,
        dwell_candidates=(2, 3),
    )
    assert set(result["arms"]) == {"N=2", "N=3"}
    for arm in result["arms"].values():
        # SDD §4's two required outputs, restored by the W-24 audit.
        assert "system_power_swing_w" in arm
        assert "angle_aware_ee_dynamic_range" in arm
        assert arm["decision_steps"] > 0
    # P2 no longer closes Q-E, and must not claim to.
    assert result["closes"] == []


@requires_archive
def test_p2_refuses_an_empty_sweep(record):
    with pytest.raises(MCRLContractError, match="at least one dwell candidate"):
        run_probe_p2(
            prereg=record,
            policy_factory=lambda: build_reference_policy(STAY_IF_POSSIBLE, 7),
            environment_factory=lambda n: _env(dwell_steps=n),
            epochs=EPOCHS,
            seed=SEED,
            dwell_candidates=(),
        )
