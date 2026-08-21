"""W-04 — 3GPP D2 candidate selection (SDD §3.2, F4).

Two things need pinning: that the threshold arithmetic reproduces F4's own
derivation, and that the latch behaves like a 3GPP event — hysteresis band,
time-to-trigger, and per-NORAD state that survives leaving the window.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import assign_satellite_slots, normalise_candidates
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.d2 import (
    THRESH2_SWEEP_KM,
    D2Config,
    D2Tracker,
    elevation_for_slant_range,
    serving_condition_entering,
    slant_range_for_elevation,
)
from mcrl.env.ephemeris import (
    SatelliteSet,
    scan_visibility,
    select_elements,
    service_area_center_ecef,
    step_times,
)
from mcrl.env.geometry import range_rate_km_s
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError

_ARCHIVE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE_ROOT.is_dir(), reason=f"TLE archive not present at {_ARCHIVE_ROOT}"
)

START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
NORADS = np.array([100, 200, 300], dtype=np.int64)
HIGH_ALTITUDE = np.full(3, 500.0)


def _tracker(config: D2Config | None = None, users: int = 1) -> D2Tracker:
    return D2Tracker(NORADS, users, config or D2Config())


def _step(tracker, step_index, slant, altitude=None, rate=None):
    slant = np.atleast_2d(np.asarray(slant, dtype=np.float64))
    return tracker.update(
        step_index,
        slant_range_km=slant,
        altitude_km=HIGH_ALTITUDE if altitude is None else np.asarray(altitude),
        range_rate_km_s=np.zeros_like(slant) if rate is None else np.atleast_2d(rate),
    )


# -- threshold arithmetic --------------------------------------------------


def test_slant_range_reproduces_F4s_own_derivation():
    """F4 states 25° -> 1123 km and 15° -> 1518 km at 550 km."""
    assert slant_range_for_elevation(25.0, 550.0) == pytest.approx(1123.0, abs=0.5)
    assert slant_range_for_elevation(15.0, 550.0) == pytest.approx(1518.0, abs=0.5)


def test_slant_and_elevation_round_trip():
    for altitude in (426.0, 485.0, 540.0, 780.0):
        for elevation in (5.0, 15.0, 25.0, 60.0, 89.0):
            slant = slant_range_for_elevation(elevation, altitude)
            assert elevation_for_slant_range(slant, altitude) == pytest.approx(
                elevation, abs=1e-6
            )


def test_zenith_slant_range_is_the_altitude():
    assert slant_range_for_elevation(90.0, 550.0) == pytest.approx(550.0, abs=1e-6)


def test_thresh2_discloses_the_measured_elevation_not_the_assumed_one():
    """Author ruling: disclose ~21.8° at the measured 485 km, not 25°."""
    config = D2Config()
    assert config.elevation_disclosure(550.0)[
        "thresh2_elevation_deg"
    ] == pytest.approx(25.8, abs=0.1)
    assert config.elevation_disclosure(485.0)[
        "thresh2_elevation_deg"
    ] == pytest.approx(21.8, abs=0.1)


def test_the_sweep_axis_is_monotone_in_elevation():
    elevations = [
        elevation_for_slant_range(threshold, 485.0)
        for threshold in THRESH2_SWEEP_KM
    ]
    assert elevations == sorted(elevations, reverse=True)
    assert elevations[0] == pytest.approx(29.3, abs=0.1)
    assert elevations[-1] == pytest.approx(16.6, abs=0.1)


def test_hysteresis_band_brackets_thresh2():
    config = D2Config()
    assert config.entry_threshold_km == 1050.0
    assert config.release_threshold_km == 1150.0
    assert config.entry_threshold_km < config.thresh2_km < config.release_threshold_km


def test_a_hysteresis_wider_than_thresh2_is_refused():
    with pytest.raises(MCRLContractError, match="hysteresis must be smaller"):
        D2Config(thresh2_km=40.0, hysteresis_km=50.0)


# -- the latch -------------------------------------------------------------


def test_a_satellite_outside_the_entry_threshold_is_not_eligible():
    tracker = _tracker()
    snapshot = _step(tracker, 0, [1200.0, 1060.0, 1051.0])
    assert not snapshot.eligible.any()


def test_ttt_delays_eligibility_by_exactly_one_step():
    """TTT counts elapsed time, so one step means the second holding step."""
    tracker = _tracker(D2Config(ttt_steps=1))
    close = [900.0, 5000.0, 5000.0]

    first = _step(tracker, 0, close)
    assert not first.eligible[0, 0]
    assert first.ttt_elapsed[0, 0] == 0

    second = _step(tracker, 1, close)
    assert second.eligible[0, 0]
    assert second.ttt_elapsed[0, 0] == 1


def test_zero_ttt_qualifies_immediately():
    tracker = _tracker(D2Config(ttt_steps=0))
    assert _step(tracker, 0, [900.0, 5000.0, 5000.0]).eligible[0, 0]


def test_a_longer_ttt_needs_a_longer_hold():
    tracker = _tracker(D2Config(ttt_steps=3))
    close = [900.0, 5000.0, 5000.0]
    for step in range(3):
        assert not _step(tracker, step, close).eligible[0, 0]
    assert _step(tracker, 3, close).eligible[0, 0]


def test_a_broken_hold_restarts_the_timer():
    """A transient dip must not accumulate toward the trigger."""
    tracker = _tracker(D2Config(ttt_steps=2))
    close = [900.0, 5000.0, 5000.0]
    far = [5000.0, 5000.0, 5000.0]
    _step(tracker, 0, close)
    _step(tracker, 1, close)
    broken = _step(tracker, 2, far)
    assert broken.ttt_elapsed[0, 0] == 0
    assert not _step(tracker, 3, close).eligible[0, 0]
    assert not _step(tracker, 4, close).eligible[0, 0]
    assert _step(tracker, 5, close).eligible[0, 0]


def test_the_latch_holds_inside_the_hysteresis_band():
    """Between entry and release the satellite stays eligible: no chatter."""
    tracker = _tracker(D2Config(ttt_steps=0))
    assert _step(tracker, 0, [900.0, 5000.0, 5000.0]).eligible[0, 0]
    # Now drifting through the band — above entry, below release.
    for step, slant in enumerate([1060.0, 1100.0, 1140.0], start=1):
        snapshot = _step(tracker, step, [slant, 5000.0, 5000.0])
        assert snapshot.eligible[0, 0], f"released at {slant} km inside the band"


def test_crossing_the_release_threshold_unlatches():
    tracker = _tracker(D2Config(ttt_steps=0))
    _step(tracker, 0, [900.0, 5000.0, 5000.0])
    assert not _step(tracker, 1, [1151.0, 5000.0, 5000.0]).eligible[0, 0]


def test_re_entry_requires_the_timer_again():
    tracker = _tracker(D2Config(ttt_steps=1))
    close = [900.0, 5000.0, 5000.0]
    _step(tracker, 0, close)
    _step(tracker, 1, close)
    _step(tracker, 2, [1200.0, 5000.0, 5000.0])
    assert not _step(tracker, 3, close).eligible[0, 0]
    assert _step(tracker, 4, close).eligible[0, 0]


# -- altitude floor --------------------------------------------------------


def test_a_re_entering_object_is_never_a_candidate():
    """SGP4 propagates a decaying satellite happily; the floor is the guard."""
    tracker = _tracker(D2Config(ttt_steps=0))
    low = np.array([156.0, 500.0, 500.0])
    snapshot = _step(tracker, 0, [400.0, 5000.0, 5000.0], altitude=low)
    assert not snapshot.eligible[0, 0]


def test_dropping_below_the_floor_unlatches_an_eligible_satellite():
    tracker = _tracker(D2Config(ttt_steps=0))
    assert _step(tracker, 0, [900.0, 5000.0, 5000.0]).eligible[0, 0]
    decayed = np.array([250.0, 500.0, 500.0])
    assert not _step(
        tracker, 1, [900.0, 5000.0, 5000.0], altitude=decayed
    ).eligible[0, 0]


# -- state is per NORAD and persists --------------------------------------


def test_state_persists_for_a_satellite_outside_the_four_slot_window():
    """§4A.6 r7: per-satellite state binds to NORAD, not to slot occupancy.

    The tracker's universe is the whole screened set, so a satellite that
    drops out of the four slots keeps its latch and re-enters without
    re-serving its TTT.
    """
    tracker = D2Tracker(np.arange(100, 110, dtype=np.int64), 1, D2Config(ttt_steps=1))
    close = np.full((1, 10), 900.0)
    altitude = np.full(10, 500.0)
    rate = np.zeros((1, 10))
    tracker.update(0, slant_range_km=close, altitude_km=altitude, range_rate_km_s=rate)
    snapshot = tracker.update(
        1, slant_range_km=close, altitude_km=altitude, range_rate_km_s=rate
    )
    # All ten are eligible, but only four can hold slots.
    assert int(snapshot.eligible.sum()) == 10
    assignment = assign_satellite_slots(
        normalise_candidates(snapshot.candidates_for_user(0)), incumbent_norad=None
    )
    assert all(assignment.occupied)
    # The six that missed out keep their latches for the next step.
    later = tracker.update(
        2, slant_range_km=close, altitude_km=altitude, range_rate_km_s=rate
    )
    assert int(later.eligible.sum()) == 10


def test_users_latch_independently():
    tracker = _tracker(D2Config(ttt_steps=0), users=2)
    slant = np.array([[900.0, 5000.0, 5000.0], [5000.0, 5000.0, 5000.0]])
    snapshot = tracker.update(
        0,
        slant_range_km=slant,
        altitude_km=HIGH_ALTITUDE,
        range_rate_km_s=np.zeros_like(slant),
    )
    assert snapshot.eligible[0, 0]
    assert not snapshot.eligible[1, 0]


def test_reset_clears_every_latch():
    tracker = _tracker(D2Config(ttt_steps=0))
    _step(tracker, 0, [900.0, 5000.0, 5000.0])
    assert tracker.latched.any()
    tracker.reset()
    assert not tracker.latched.any()


def test_column_lookup_fails_loud_for_an_unknown_norad():
    tracker = _tracker()
    assert tracker.column_for(200) == 1
    with pytest.raises(MCRLContractError, match="not in this tracker's universe"):
        tracker.column_for(999)


def test_duplicate_norads_are_refused():
    with pytest.raises(MCRLContractError, match="unique"):
        D2Tracker(np.array([1, 1]), 1)


def test_misshaped_measurements_fail_loud():
    tracker = _tracker()
    with pytest.raises(MCRLContractError, match="slant_range_km"):
        tracker.update(
            0,
            slant_range_km=np.zeros((1, 2)),
            altitude_km=HIGH_ALTITUDE,
            range_rate_km_s=np.zeros((1, 2)),
        )
    with pytest.raises(MCRLContractError, match="altitude_km"):
        tracker.update(
            0,
            slant_range_km=np.zeros((1, 3)),
            altitude_km=np.zeros(2),
            range_rate_km_s=np.zeros((1, 3)),
        )


def test_non_finite_measurements_fail_loud():
    tracker = _tracker()
    with pytest.raises(MCRLContractError, match="finite"):
        _step(tracker, 0, [np.nan, 900.0, 900.0])


# -- margin feeds the slot ordering ---------------------------------------


def test_margin_is_larger_for_a_closer_satellite():
    tracker = _tracker(D2Config(ttt_steps=0))
    snapshot = _step(tracker, 0, [600.0, 800.0, 1000.0])
    candidates = snapshot.candidates_for_user(0)
    assert [c.norad_id for c in candidates] == [100, 200, 300]
    assert candidates[0].margin_km > candidates[1].margin_km > candidates[2].margin_km
    assignment = assign_satellite_slots(
        normalise_candidates(candidates), incumbent_norad=None
    )
    assert assignment.norad_ids[:3] == (100, 200, 300)


def test_candidates_carry_the_signed_range_rate():
    tracker = _tracker(D2Config(ttt_steps=0))
    snapshot = _step(
        tracker, 0, [600.0, 700.0, 800.0], rate=[[-6.1, 0.0, 5.4]]
    )
    rates = {c.norad_id: c.radial_rate_km_s for c in snapshot.candidates_for_user(0)}
    assert rates[100] < 0 < rates[300]


def test_only_eligible_satellites_become_candidates():
    tracker = _tracker(D2Config(ttt_steps=0))
    snapshot = _step(tracker, 0, [600.0, 5000.0, 800.0])
    assert [c.norad_id for c in snapshot.candidates_for_user(0)] == [100, 300]


# -- the serving-side condition exists but is off the baseline path -------


def test_serving_condition_is_implemented_for_C4():
    config = D2Config()
    result = serving_condition_entering(np.array([1400.0, 1560.0]), config)
    assert result.tolist() == [False, True]


def test_serving_condition_is_not_referenced_by_the_tracker():
    """SDD §3.2: the baseline uses the candidate side only."""
    import inspect

    from mcrl.env import d2

    source = inspect.getsource(d2.D2Tracker)
    assert "serving_condition_entering" not in source
    assert "thresh1" not in source.lower()


# -- against the real ephemeris -------------------------------------------


@requires_archive
def test_d2_over_a_real_pass_produces_a_plausible_candidate_set():
    archive = TleArchive(_ARCHIVE_ROOT)
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    steps = 60
    config = D2Config()
    warmup = config.warmup_steps
    origin = START - dt.timedelta(seconds=warmup * config.time_step_s)
    jd, fr = step_times(origin, steps + warmup)
    healthy = satellites.healthy_indices(jd, fr)
    subset = satellites.subset(healthy)

    ground = service_area_center_ecef()
    position, velocity = subset.propagate_ecef_state(jd, fr)
    slant = np.linalg.norm(position - ground, axis=-1)
    altitude = np.linalg.norm(position, axis=-1) - 6371.0
    rate = range_rate_km_s(position, velocity, ground)

    tracker = D2Tracker(subset.norad_ids, 1, config)
    tracker.prime(
        slant_range_km=slant[None, :, :warmup],
        altitude_km=altitude[:, :warmup],
        range_rate_km_s=rate[None, :, :warmup],
    )
    slant, altitude, rate = (
        slant[:, warmup:],
        altitude[:, warmup:],
        rate[:, warmup:],
    )
    counts = []
    for step in range(steps):
        snapshot = tracker.update(
            step,
            slant_range_km=slant[None, :, step],
            altitude_km=altitude[:, step],
            range_rate_km_s=rate[None, :, step],
        )
        counts.append(int(snapshot.eligible_counts[0]))

    # There must be candidates, and far more than the four slots can hold,
    # so D2 is genuinely selective rather than a formality.
    assert min(counts) > 0
    assert max(counts) > 4
    assert max(counts) < 200
    # Eligibility must change over a minute — satellites move.
    assert len(set(counts)) > 1


@requires_archive
def test_every_eligible_satellite_is_inside_the_release_threshold():
    archive = TleArchive(_ARCHIVE_ROOT)
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    jd, fr = step_times(START, 10)
    healthy = satellites.healthy_indices(jd, fr)
    subset = satellites.subset(healthy)

    ground = service_area_center_ecef()
    position, velocity = subset.propagate_ecef_state(jd, fr)
    slant = np.linalg.norm(position - ground, axis=-1)
    altitude = np.linalg.norm(position, axis=-1) - 6371.0
    rate = range_rate_km_s(position, velocity, ground)

    config = D2Config()
    tracker = D2Tracker(subset.norad_ids, 1, config)
    for step in range(10):
        snapshot = tracker.update(
            step,
            slant_range_km=slant[None, :, step],
            altitude_km=altitude[:, step],
            range_rate_km_s=rate[None, :, step],
        )
        eligible = snapshot.eligible[0]
        if not eligible.any():
            continue
        assert slant[eligible, step].max() <= config.release_threshold_km
        assert altitude[eligible, step].min() >= config.min_altitude_km


# -- warm-up: the episode boundary must not manufacture an outage ---------


def test_a_cold_tracker_has_no_candidates_on_the_first_step():
    """The behaviour warm-up exists to prevent."""
    tracker = _tracker(D2Config(ttt_steps=1))
    assert not _step(tracker, 0, [900.0, 900.0, 900.0]).eligible.any()


def test_priming_makes_step_zero_immediately_usable():
    config = D2Config(ttt_steps=1)
    tracker = _tracker(config)
    warmup = config.warmup_steps
    close = np.full((1, 3, warmup), 900.0)
    tracker.prime(
        slant_range_km=close,
        altitude_km=np.full((3, warmup), 500.0),
        range_rate_km_s=np.zeros((1, 3, warmup)),
    )
    assert tracker.primed
    assert _step(tracker, 0, [900.0, 900.0, 900.0]).eligible.all()


def test_warmup_length_covers_the_configured_ttt():
    assert D2Config(ttt_steps=0).warmup_steps == 1
    assert D2Config(ttt_steps=1).warmup_steps == 1
    assert D2Config(ttt_steps=5).warmup_steps == 5


def test_a_longer_ttt_needs_its_full_warmup():
    config = D2Config(ttt_steps=4)
    tracker = _tracker(config)
    warmup = config.warmup_steps
    assert warmup == 4
    tracker.prime(
        slant_range_km=np.full((1, 3, warmup), 900.0),
        altitude_km=np.full((3, warmup), 500.0),
        range_rate_km_s=np.zeros((1, 3, warmup)),
    )
    assert _step(tracker, 0, [900.0, 900.0, 900.0]).eligible.all()


def test_priming_with_too_short_a_window_fails_loud():
    config = D2Config(ttt_steps=4)
    tracker = _tracker(config)
    with pytest.raises(MCRLContractError, match="warm-up steps"):
        tracker.prime(
            slant_range_km=np.full((1, 3, 2), 900.0),
            altitude_km=np.full((3, 2), 500.0),
            range_rate_km_s=np.zeros((1, 3, 2)),
        )


def test_priming_does_not_qualify_a_satellite_that_is_still_far():
    config = D2Config(ttt_steps=1)
    tracker = _tracker(config)
    tracker.prime(
        slant_range_km=np.full((1, 3, 1), 5000.0),
        altitude_km=np.full((3, 1), 500.0),
        range_rate_km_s=np.zeros((1, 3, 1)),
    )
    assert not _step(tracker, 0, [5000.0, 5000.0, 5000.0]).eligible.any()


@requires_archive
def test_priming_removes_the_first_step_outage_on_real_geometry():
    """Without warm-up every user is unserved at step 0 of every episode.

    Under PATCH P-03 that drops the transition, so a H=10 episode would
    discard 10% of its decision steps and trip the §4A.5a(4) outage gate for
    a reason that is an artefact of the episode boundary.
    """
    archive = TleArchive(_ARCHIVE_ROOT)
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    config = D2Config()
    warmup = config.warmup_steps
    origin = START - dt.timedelta(seconds=warmup * config.time_step_s)
    jd, fr = step_times(origin, 10 + warmup)
    subset = satellites.subset(satellites.healthy_indices(jd, fr))

    ground = service_area_center_ecef()
    position, velocity = subset.propagate_ecef_state(jd, fr)
    slant = np.linalg.norm(position - ground, axis=-1)[None, :, :]
    altitude = np.linalg.norm(position, axis=-1) - 6371.0
    rate = range_rate_km_s(position, velocity, ground)[None, :, :]

    cold = D2Tracker(subset.norad_ids, 1, config)
    first_cold = cold.update(
        0,
        slant_range_km=slant[:, :, warmup],
        altitude_km=altitude[:, warmup],
        range_rate_km_s=rate[:, :, warmup],
    )
    assert int(first_cold.eligible_counts[0]) == 0

    warm = D2Tracker(subset.norad_ids, 1, config)
    warm.prime(
        slant_range_km=slant[:, :, :warmup],
        altitude_km=altitude[:, :warmup],
        range_rate_km_s=rate[:, :, :warmup],
    )
    first_warm = warm.update(
        0,
        slant_range_km=slant[:, :, warmup],
        altitude_km=altitude[:, warmup],
        range_rate_km_s=rate[:, :, warmup],
    )
    assert int(first_warm.eligible_counts[0]) > 4
