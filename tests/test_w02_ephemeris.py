"""W-02 — element selection (F3), the date split, propagation, visibility."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.constants import R_E_KM, TLE_ROOT_DEFAULT
from mcrl.env.ephemeris import (
    TEST,
    TRAIN,
    BlockAlternatingSplit,
    ContiguousDateSplit,
    EphemerisConfig,
    EphemerisError,
    EpisodeStartSampler,
    SatelliteSet,
    build_freeze_manifest,
    file_set_hash,
    scan_visibility,
    select_elements,
    service_area_center_ecef,
    shortlist_visible,
    step_times,
    write_freeze_manifest,
)
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError

_ARCHIVE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE_ROOT.is_dir(), reason=f"TLE archive not present at {_ARCHIVE_ROOT}"
)

START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)


@pytest.fixture(scope="module")
def archive() -> TleArchive:
    return TleArchive(_ARCHIVE_ROOT)


# -- time grid -------------------------------------------------------------


def test_step_times_advances_only_the_fraction():
    jd, fr = step_times(START, 10, time_step_s=1.0)
    assert jd.shape == fr.shape == (10,)
    assert len(set(jd.tolist())) == 1, "the day must not move under a 1 s step"
    deltas = np.diff(fr) * 86400.0
    assert np.allclose(deltas, 1.0, atol=1e-9)


def test_step_times_rejects_an_empty_horizon():
    with pytest.raises(ValueError):
        step_times(START, 0)


# -- date split (SDD F3) ---------------------------------------------------


def test_split_rejects_overlapping_ranges():
    with pytest.raises(MCRLContractError, match="interleav"):
        ContiguousDateSplit(
            train_start=dt.date(2025, 7, 27),
            train_end=dt.date(2026, 6, 1),
            test_start=dt.date(2026, 5, 1),
            test_end=dt.date(2026, 8, 20),
        )


def test_split_accepts_adjacent_ranges():
    split = ContiguousDateSplit(
        train_start=dt.date(2025, 7, 27),
        train_end=dt.date(2026, 5, 31),
        test_start=dt.date(2026, 6, 1),
        test_end=dt.date(2026, 8, 20),
    )
    assert split.dates_for("train")[1] < split.dates_for("test")[0]


@requires_archive
def test_chronological_split_is_ordered_and_covers_the_corpus(archive):
    split = ContiguousDateSplit.chronological(archive, test_fraction=0.2)
    assert split.train_start == archive.dates[0]
    assert split.test_end == archive.dates[-1]
    assert split.train_end < split.test_start
    train_files = split.available_dates(archive, "train")
    test_files = split.available_dates(archive, "test")
    assert len(train_files) + len(test_files) == len(archive.dates)
    assert len(test_files) == pytest.approx(0.2 * len(archive.dates), abs=1)
    # The corpus is 373 files over a 390-day span: 17 dates have no file, so
    # counting calendar days instead of files would be wrong here.
    assert (split.test_end - split.train_start).days + 1 > len(archive.dates)


@requires_archive
def test_sampler_stays_inside_its_own_half(archive):
    split = ContiguousDateSplit.chronological(archive)
    rng = np.random.default_rng(11)
    train = EpisodeStartSampler.for_archive(archive, split, "train")
    test = EpisodeStartSampler.for_archive(archive, split, "test")
    train_dates = set(split.available_dates(archive, "train"))
    test_dates = set(split.available_dates(archive, "test"))
    for _ in range(200):
        drawn = train.draw(rng)
        assert split.train_start <= drawn.date() <= split.train_end
        assert drawn.date() in train_dates, "must never draw a date with no file"
        drawn = test.draw(rng)
        assert split.test_start <= drawn.date() <= split.test_end
        assert drawn.date() in test_dates


@requires_archive
def test_sampler_is_deterministic_given_a_seed(archive):
    split = ContiguousDateSplit.chronological(archive)
    sampler = EpisodeStartSampler.for_archive(archive, split, "train")
    first = [sampler.draw(np.random.default_rng(5)) for _ in range(3)]
    second = [sampler.draw(np.random.default_rng(5)) for _ in range(3)]
    assert first == second


def test_sampler_snaps_to_the_time_step():
    sampler = EpisodeStartSampler(
        TRAIN,
        available_dates=(dt.date(2026, 1, 1), dt.date(2026, 1, 2)),
        time_step_s=10.0,
    )
    rng = np.random.default_rng(0)
    for _ in range(50):
        drawn = sampler.draw(rng)
        assert drawn.second % 10 == 0 and drawn.microsecond == 0


# -- element selection (SDD F3) -------------------------------------------


@requires_archive
def test_selection_respects_the_age_ceiling(archive):
    selection = select_elements(archive, START, max_age_h=24.0)
    ages = selection.ages_h
    assert ages.size > 5_000
    assert ages.max() <= 24.0
    assert selection.rejected_stale > 0, "the corpus does contain stale elements"
    assert selection.considered_norads == len(selection.records) + selection.rejected_stale


@requires_archive
def test_a_tighter_ceiling_selects_a_strict_subset(archive):
    wide = select_elements(archive, START, max_age_h=24.0)
    tight = select_elements(archive, START, max_age_h=6.0)
    assert tight.ages_h.max() <= 6.0
    assert len(tight.records) < len(wide.records)
    assert set(r.norad_id for r in tight.records) <= set(
        r.norad_id for r in wide.records
    )


@requires_archive
def test_widening_the_file_window_lowers_the_median_age(archive):
    """A single daily file spans ~21 days of epochs; neighbours help."""
    narrow = select_elements(archive, START, search_days=0)
    wide = select_elements(archive, START, search_days=1)
    assert len(wide.records) >= len(narrow.records)
    # The real invariant is pointwise: taking the min over a superset of
    # files can only lower each satellite's age.  (The bulk median moves by
    # rounding alone, so asserting on it would be testing noise.)
    wide_ages = {
        record.norad_id: record.age_seconds(START) for record in wide.records
    }
    for record in narrow.records:
        assert wide_ages[record.norad_id] <= record.age_seconds(START) + 1e-9


@requires_archive
def test_selection_picks_the_nearest_epoch_per_norad(archive):
    selection = select_elements(archive, START, search_days=1)
    chosen = {record.norad_id: record for record in selection.records}
    for file_date in selection.source_dates:
        for candidate in archive.load(file_date).records:
            winner = chosen.get(candidate.norad_id)
            if winner is None:
                continue
            assert winner.age_seconds(START) <= candidate.age_seconds(START)


@requires_archive
def test_selection_outside_the_corpus_fails_loud(archive):
    with pytest.raises(EphemerisError, match="no TLE file"):
        select_elements(
            archive, dt.datetime(2020, 1, 1, tzinfo=dt.timezone.utc)
        )


def test_selection_requires_an_aware_datetime(archive=None):
    class _Stub:
        def has(self, _d):
            return False

    with pytest.raises(ValueError, match="timezone-aware"):
        select_elements(_Stub(), dt.datetime(2026, 8, 20))


# -- propagation -----------------------------------------------------------


@requires_archive
def test_propagated_altitudes_are_physically_plausible(archive):
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records[:400])
    jd, fr = step_times(START, 10)
    healthy = satellites.healthy_indices(jd, fr)
    assert healthy.size > 300
    ecef = satellites.subset(healthy).propagate_ecef(jd, fr)
    altitude = np.linalg.norm(ecef, axis=-1) - R_E_KM
    # The corpus contains actively deorbiting satellites: the lowest healthy
    # object in this window sits near 156 km.  W-04 has to exclude those from
    # D2 candidacy; here the check is only that nothing is absurd.
    assert altitude.min() > 100.0
    assert altitude.max() < 2_000.0
    assert 350.0 < float(np.median(altitude)) < 700.0


@requires_archive
def test_ecef_positions_rotate_with_the_earth(archive):
    """Over 10 s an ECEF ground track must move, and by a sane amount."""
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records[:200])
    jd, fr = step_times(START, 11)
    healthy = satellites.healthy_indices(jd, fr)
    ecef = satellites.subset(healthy).propagate_ecef(jd, fr)
    step_km = np.linalg.norm(np.diff(ecef, axis=1), axis=-1)
    # LEO ground speed is ~7.5 km/s; Earth rotation adds/removes ~0.35 km/s.
    assert step_km.min() > 5.0
    assert step_km.max() < 9.0


@requires_archive
def test_propagate_ecef_fails_loud_on_an_sgp4_error(archive):
    """Deep extrapolation decays low objects; that must abort, not return NaN.

    Every element set is healthy at its own epoch, so the failure has to be
    provoked: 120 days past epoch, ~4% of this corpus hits SGP4 error 1 or 6.
    """
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    far_future = START + dt.timedelta(days=120)
    jd, fr = step_times(far_future, 2)

    healthy = satellites.healthy_indices(jd, fr)
    assert 0 < healthy.size < len(satellites)

    with pytest.raises(EphemerisError, match="SGP4 error"):
        satellites.propagate_ecef(jd, fr)

    # The healthy subset still propagates, and opting out of the check
    # returns without raising.
    assert satellites.subset(healthy).propagate_ecef(jd, fr).shape == (
        healthy.size,
        2,
        3,
    )
    assert satellites.propagate_ecef(
        jd, fr, require_all_healthy=False
    ).shape == (len(satellites), 2, 3)


@requires_archive
def test_every_selected_element_is_healthy_at_its_own_start(archive):
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    jd, fr = step_times(START, 10)
    assert satellites.healthy_indices(jd, fr).size == len(satellites)


def test_satellite_set_rejects_an_empty_record_list():
    with pytest.raises(EphemerisError):
        SatelliteSet([])


# -- visibility ------------------------------------------------------------


@requires_archive
def test_service_area_sees_a_plausible_number_of_satellites(archive):
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    jd, fr = step_times(START, 1)
    healthy = satellites.healthy_indices(jd, fr)
    scan = scan_visibility(satellites.subset(healthy), jd, fr)
    for min_elevation in (10.0, 25.0, 40.0):
        count = int(np.count_nonzero(scan.visible(min_elevation)[:, 0]))
        assert count > 0, f"nothing visible above {min_elevation}°"
        assert count < 500, f"{count} satellites above {min_elevation}° is absurd"
    assert int(np.count_nonzero(scan.visible(10.0)[:, 0])) > int(
        np.count_nonzero(scan.visible(40.0)[:, 0])
    )


@requires_archive
def test_shortlist_is_a_superset_of_what_the_fine_scan_finds(archive):
    """The coarse pre-filter must not drop a satellite the fine grid sees."""
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records)
    duration_s = 120.0
    short = shortlist_visible(
        satellites,
        START,
        duration_s=duration_s,
        coarse_step_s=30.0,
        min_elevation_deg=25.0,
    )
    jd, fr = step_times(START, int(duration_s) + 1, time_step_s=1.0)
    healthy = satellites.healthy_indices(jd, fr)
    fine = scan_visibility(satellites.subset(healthy), jd, fr)
    fine_ids = set(
        satellites.subset(healthy).norad_ids[
            fine.ever_visible_indices(25.0)
        ].tolist()
    )
    short_ids = set(satellites.norad_ids[short].tolist())
    assert fine_ids, "no satellite visible at all in the fine scan"
    assert fine_ids <= short_ids


@requires_archive
def test_elevation_and_off_nadir_move_together(archive):
    selection = select_elements(archive, START)
    satellites = SatelliteSet(selection.records[:600])
    jd, fr = step_times(START, 1)
    healthy = satellites.healthy_indices(jd, fr)
    scan = scan_visibility(satellites.subset(healthy), jd, fr)
    visible = scan.visible(20.0)[:, 0]
    if not visible.any():
        pytest.skip("nothing visible in this subset")
    elevation = scan.elevation_deg[visible, 0]
    off_nadir = scan.off_nadir_deg[visible, 0]
    # Higher elevation means the user sits closer to the satellite's nadir.
    assert np.corrcoef(elevation, off_nadir)[0, 1] < -0.9


def test_service_area_center_sits_on_the_sphere():
    center = service_area_center_ecef()
    assert float(np.linalg.norm(center)) == pytest.approx(R_E_KM, abs=1e-9)


# -- freeze manifest -------------------------------------------------------


def test_file_set_hash_is_order_independent():
    rows = [
        {"file": "b.tle", "sha256": "22"},
        {"file": "a.tle", "sha256": "11"},
    ]
    assert file_set_hash(rows) == file_set_hash(list(reversed(rows)))


def test_file_set_hash_changes_with_content():
    base = [{"file": "a.tle", "sha256": "11"}]
    changed = [{"file": "a.tle", "sha256": "12"}]
    assert file_set_hash(base) != file_set_hash(changed)


@requires_archive
def test_freeze_manifest_carries_everything_section_7_1_names(archive, tmp_path):
    config = EphemerisConfig(tle_root=str(_ARCHIVE_ROOT))
    split = ContiguousDateSplit.chronological(archive)
    manifest = build_freeze_manifest(
        config,
        split,
        sampled_dates=[dt.date(2026, 8, 19), dt.date(2026, 8, 20)],
        start_utc=START,
    )
    assert manifest["schema"] == "mcrl-ephemeris-freeze-v1"
    assert len(manifest["frozen_files"]) == 2
    assert len(manifest["file_set_sha256"]) == 64
    assert manifest["split"]["train_end"] < manifest["split"]["test_start"]
    assert manifest["sgp4"]["gravity_model"] == "wgs72"
    assert manifest["config"]["time_step_s"] == 1.0
    assert manifest["element_selection"]["age_hours"]["max_h"] <= 24.0
    assert manifest["sampling"]["train"]["part"] == "train"

    path = write_freeze_manifest(tmp_path / "freeze.json", manifest)
    assert json.loads(path.read_text())["file_set_sha256"] == manifest[
        "file_set_sha256"
    ]
