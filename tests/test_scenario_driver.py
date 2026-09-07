"""Episode driver: epoch in, candidate tables out.

Everything here is settled by the paper or by earlier rulings; the physics
half is deliberately absent, so P1 can run while the power model is open.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.d2 import D2Config
from mcrl.env.dwell import DwellConfig
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import STAY_IF_POSSIBLE, build_reference_policy
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError
from mcrl.runtime.prereg import freeze_prereg
from mcrl.runtime.probe_p1 import run_probe_p1

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
USERS = 20


@pytest.fixture(scope="module")
def driver():
    return ScenarioDriver(
        TleArchive(_ARCHIVE),
        ScenarioConfig(mobility=MobilityConfig(num_users=USERS)),
    )


@requires_archive
def test_reset_yields_a_usable_step_zero(driver):
    candidates = driver.reset(START, np.random.default_rng(0))
    assert len(candidates.slot_tables) == USERS
    assert candidates.masks.shape == (USERS, NUM_ACTIONS)
    assert driver.step_index == 0


@requires_archive
def test_the_d2_latches_are_warm_at_step_zero(driver):
    """W-04: a cold tracker would starve everyone on the first step."""
    candidates = driver.reset(START, np.random.default_rng(0))
    assert not candidates.starved_users.any()
    assert np.all(candidates.d2.eligible_counts > 4)


@requires_archive
def test_the_tracked_universe_is_screened_and_then_fixed(driver):
    """§4A.6 r7: per-NORAD state must survive leaving the window."""
    driver.reset(START, np.random.default_rng(0))
    tracked = driver.tracked_norad_ids.copy()
    assert 0 < tracked.size < 5000, "the screen should cut ~10,000 satellites"
    for _ in range(5):
        driver.step(np.random.default_rng(1))
    assert np.array_equal(driver.tracked_norad_ids, tracked)


@requires_archive
def test_windows_differ_across_users_on_real_geometry(driver):
    """The paper writes b_u(c,t) with a u subscript; here is why."""
    candidates = driver.reset(START, np.random.default_rng(0))
    windows = {tuple(row.tolist()) for row in candidates.window_norad_ids}
    assert len(windows) > 1


@requires_archive
def test_an_episode_yields_the_configured_number_of_steps(driver):
    steps = list(driver.episode(START, np.random.default_rng(0)))
    assert len(steps) == driver.config.steps_per_episode
    assert all(not step.starved_users.any() for step in steps)


@requires_archive
def test_users_move_and_satellites_move(driver):
    first = driver.reset(START, np.random.default_rng(0))
    later = first
    for _ in range(5):
        later = driver.step(np.random.default_rng(1))
    assert not np.array_equal(
        first.window_satellite_ecef_km, later.window_satellite_ecef_km
    )
    assert not np.array_equal(
        first.dwell.anchor_cell_ids.astype(float),
        later.slant_range_km[:, 0],
    )


@requires_archive
def test_the_dwell_boundary_falls_where_the_config_says(driver):
    driver.reset(START, np.random.default_rng(0))
    boundaries = [0]
    for index in range(1, 9):
        if driver.step(np.random.default_rng(1)).dwell.is_boundary:
            boundaries.append(index)
    # Derived from the frozen N, not hard-coded: Q-E moved from 3 to 4 on
    # 2026-08-23 and a literal here would assert the old scenario while
    # claiming to assert the boundary rule.
    n = driver.config.dwell.steps
    assert boundaries == [step for step in range(10) if step % n == 0]


@requires_archive
def test_an_incumbent_is_honoured_through_the_driver(driver):
    plain = driver.reset(START, np.random.default_rng(0))
    other = plain.window_norad_ids[:, 2].copy()
    withheld = driver.reset(
        START, np.random.default_rng(0), incumbent_norads=other
    )
    assert np.array_equal(withheld.window_norad_ids[:, 0], other)


@requires_archive
def test_candidate_slot_identities_do_not_reorder_inside_a_dwell(driver):
    """B6: an incumbent change cannot silently rename the action slots."""
    first = driver.reset(START, np.random.default_rng(0))
    new_incumbents = first.window_norad_ids[:, 2].copy()

    # Step 1 is inside the N=4 dwell.  Without the boundary cache, the
    # ordinary assignment rule would move every requested incumbent to slot
    # zero and this assertion would fail for a reason forced by the test.
    second = driver.step(
        np.random.default_rng(1), incumbent_norads=new_incumbents
    )
    assert not second.dwell.is_boundary
    assert np.array_equal(second.window_norad_ids, first.window_norad_ids)
    assert np.all(
        [assignment.is_incumbent[2] for assignment in second.assignments]
    )


@requires_archive
def test_stepping_before_reset_fails_loud():
    driver = ScenarioDriver(
        TleArchive(_ARCHIVE), ScenarioConfig(mobility=MobilityConfig(num_users=4))
    )
    with pytest.raises(MCRLContractError, match="has not been reset"):
        driver.step(np.random.default_rng(0))


def test_a_naive_datetime_is_refused(driver=None):
    with pytest.raises(ValueError, match="timezone-aware"):
        ScenarioDriver.reset(
            object.__new__(ScenarioDriver),
            dt.datetime(2026, 8, 20, 6, 0),
            np.random.default_rng(0),
        )


@requires_archive
def test_the_configuration_round_trips_for_the_prereg(driver):
    payload = driver.config.as_dict()
    assert payload["steps_per_episode"] == 10
    assert payload["d2"]["thresh2_km"] == 1100.0
    assert payload["mobility"]["boundary"] == "reflection"
    assert payload["grid_altitude_km"] == 483.0


# -- P1 end to end ---------------------------------------------------------


SELECTION_MAPPINGS = {
    "Q-E dwell N": "N maximising the angle-aware EE dynamic range in P2",
    "Q-D r3 calibration scale": "p95 of |U_{b_u}| over the P3 reference rollout",
}


def _prereg():
    sections = {
        name: {"placeholder": True}
        for name in (
            "ephemeris",
            "split",
            "sampling",
            "d2",
            "antenna_and_link_budget",
            "dwell",
            "reward",
            "action_and_state",
            "training",
            "thresholds",
            "stopping_rules",
            "reference_policy",
            "pointing_cells",
        )
    }
    sections["probe_grid"] = {"P1": {"visibility": True, "d2_event_rate": True}}
    sections["selection_mappings"] = SELECTION_MAPPINGS
    return freeze_prereg(sections, holdout_seed=20260822)


@requires_archive
def test_probe_p1_runs_against_the_real_driver(driver):
    """The plumbing check.  NOT a probe result — the PREREG here is a stub
    and the mask still lacks its link-feasibility term."""
    rng = np.random.default_rng(11)
    result = run_probe_p1(
        prereg=_prereg(),
        policy=build_reference_policy(STAY_IF_POSSIBLE, seed=1),
        steps=driver.episode(START, rng),
        rng=rng,
    )
    assert result["probe"] == "P1"
    assert result["decision_steps"] == USERS * driver.config.steps_per_episode
    assert 0.0 <= result["starvation_rate"] <= 1.0
    assert 0.0 <= result["handover_rate"] <= 1.0
    assert result["d2_eligible_per_user"]["p50"] > 4
    assert 0.0 < result["elevation_deg"]["p50"] < 90.0
    # Ruling C-11: link feasibility is an execution-time outage, not a
    # mask term, so the mask has three terms and says so.
    assert "execution-time outage" in result["mask_scope"]


@requires_archive
def test_a_holding_policy_produces_fewer_handovers_than_a_random_one(driver):
    """The sanity check that makes a measured event rate meaningful."""
    from mcrl.env.reference_policy import RANDOM_MASKED

    prereg = _prereg()
    holding = run_probe_p1(
        prereg=prereg,
        policy=build_reference_policy(STAY_IF_POSSIBLE, 1),
        steps=driver.episode(START, np.random.default_rng(3)),
        rng=np.random.default_rng(3),
    )
    churning = run_probe_p1(
        prereg=prereg,
        policy=build_reference_policy(RANDOM_MASKED, 1),
        steps=driver.episode(START, np.random.default_rng(3)),
        rng=np.random.default_rng(3),
    )
    assert holding["handover_rate"] < churning["handover_rate"]
