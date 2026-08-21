"""W-02 — TLE parsing, checksums, and the daily-file archive."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.tle import (
    MAX_MALFORMED_RECORD_FRACTION,
    TleArchive,
    TleDailyFile,
    TleFormatError,
    TleQuarantineError,
    parse_epoch,
    parse_tle_text,
    tle_checksum,
)
from mcrl.errors import MCRLContractError

_L1 = "1 44714U 19074B   26232.06002532  .00074166  00000+0  87102-3 0  9998"
_L2 = "2 44714  53.1475 120.5458 0005540  67.9434 292.2167 15.60812453374153"
_GOOD = f"STARLINK-1008\n{_L1}\n{_L2}\n"

_ARCHIVE_ROOT = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE_ROOT.is_dir(), reason=f"TLE archive not present at {_ARCHIVE_ROOT}"
)


def test_checksum_matches_the_published_lines():
    assert tle_checksum(_L1) == int(_L1[68])
    assert tle_checksum(_L2) == int(_L2[68])


def test_parse_epoch_decodes_year_and_day_fraction():
    epoch = parse_epoch(_L1)
    assert epoch.tzinfo is dt.timezone.utc
    assert epoch.year == 2026
    # DOY 232.06002532 of 2026 -> 2026-08-20 01:26:26 UTC
    assert (epoch - dt.datetime(2026, 8, 20, tzinfo=dt.timezone.utc)).total_seconds() \
        == pytest.approx(0.06002532 * 86400.0, abs=1e-3)


def test_parse_epoch_applies_the_tle_century_rule():
    line_1957 = _L1[:18] + "57001.00000000" + _L1[32:]
    line_2000 = _L1[:18] + "00001.00000000" + _L1[32:]
    assert parse_epoch(line_1957).year == 1957
    assert parse_epoch(line_2000).year == 2000


def test_parse_round_trip():
    records, quarantined = parse_tle_text(_GOOD)
    assert not quarantined
    (record,) = records
    assert record.norad_id == 44714
    assert record.name == "STARLINK-1008"
    assert record.line1 == _L1


def test_age_is_absolute():
    (record,), _ = parse_tle_text(_GOOD)
    before = record.epoch_utc - dt.timedelta(hours=3)
    after = record.epoch_utc + dt.timedelta(hours=3)
    assert record.age_seconds(before) == pytest.approx(3 * 3600.0)
    assert record.age_seconds(after) == pytest.approx(3 * 3600.0)


def test_bad_checksum_is_quarantined_not_silently_kept():
    corrupted = _L1[:68] + str((int(_L1[68]) + 1) % 10)
    records, quarantined = parse_tle_text(f"NAME\n{corrupted}\n{_L2}\n")
    assert records == []
    assert len(quarantined) == 1
    assert "checksum" in quarantined[0].reason
    assert quarantined[0].line1 == corrupted


def test_swapped_line_numbers_are_quarantined():
    _records, quarantined = parse_tle_text(f"NAME\n{_L2}\n{_L1}\n")
    assert "line number" in quarantined[0].reason


def test_mismatched_norad_ids_are_quarantined():
    other = "2 44718  53.1503 119.9226 0001985 112.7203 247.4022 15.61217091374178"
    _records, quarantined = parse_tle_text(f"NAME\n{_L1}\n{other}\n")
    assert "NORAD id mismatch" in quarantined[0].reason


def test_a_good_record_survives_alongside_a_quarantined_one():
    corrupted = _L1[:68] + str((int(_L1[68]) + 1) % 10)
    records, quarantined = parse_tle_text(
        _GOOD + f"BAD\n{corrupted}\n{_L2}\n"
    )
    assert len(records) == 1 and len(quarantined) == 1
    assert records[0].norad_id == 44714


def test_quarantine_ceiling_rejects_a_structurally_broken_file(tmp_path):
    corrupted = _L1[:68] + str((int(_L1[68]) + 1) % 10)
    path = tmp_path / "starlink_20260820.tle"
    path.write_text(f"BAD\n{corrupted}\n{_L2}\n")
    with pytest.raises(TleQuarantineError, match="malformed"):
        TleDailyFile.load(path)


def test_quarantine_ceiling_is_configurable(tmp_path):
    corrupted = _L1[:68] + str((int(_L1[68]) + 1) % 10)
    path = tmp_path / "starlink_20260820.tle"
    path.write_text(_GOOD + f"BAD\n{corrupted}\n{_L2}\n")
    daily = TleDailyFile.load(path, max_malformed_fraction=0.75)
    assert len(daily.records) == 1
    assert len(daily.quarantined) == 1
    assert daily.malformed_fraction == pytest.approx(0.5)
    assert MAX_MALFORMED_RECORD_FRACTION < 0.5


def test_truncated_input_is_rejected():
    with pytest.raises(TleFormatError, match="multiple of 3"):
        parse_tle_text(f"NAME\n{_L1}\n")


def test_bad_filename_is_rejected(tmp_path):
    path = tmp_path / "not-a-starlink-file.tle"
    path.write_text(_GOOD)
    with pytest.raises(MCRLContractError, match="filename"):
        TleDailyFile.load(path)


def test_daily_file_hashes_its_bytes(tmp_path):
    path = tmp_path / "starlink_20260820.tle"
    path.write_text(_GOOD)
    daily = TleDailyFile.load(path)
    assert daily.file_date == dt.date(2026, 8, 20)
    assert len(daily.sha256) == 64
    assert daily.by_norad[44714].name == "STARLINK-1008"


def test_duplicate_norad_in_one_file_is_rejected(tmp_path):
    path = tmp_path / "starlink_20260820.tle"
    path.write_text(_GOOD + _GOOD)
    with pytest.raises(TleFormatError, match="duplicate NORAD"):
        TleDailyFile.load(path)


def test_archive_requires_a_directory_with_files(tmp_path):
    with pytest.raises(MCRLContractError, match="not a directory"):
        TleArchive(tmp_path / "missing")
    (tmp_path / "empty").mkdir()
    with pytest.raises(MCRLContractError, match="no starlink"):
        TleArchive(tmp_path / "empty")


def test_archive_reports_a_helpful_range_on_a_missing_date(tmp_path):
    (tmp_path / "starlink_20260820.tle").write_text(_GOOD)
    archive = TleArchive(tmp_path)
    with pytest.raises(MCRLContractError, match="archive covers"):
        archive.load(dt.date(2026, 1, 1))


@requires_archive
def test_real_archive_covers_the_documented_range():
    archive = TleArchive(_ARCHIVE_ROOT)
    first, last = archive.date_range
    assert first == dt.date(2025, 7, 27)
    assert last == dt.date(2026, 8, 20)
    assert len(archive.dates) == 373


@requires_archive
def test_every_record_of_a_real_daily_file_validates():
    archive = TleArchive(_ARCHIVE_ROOT)
    daily = archive.load(dt.date(2026, 8, 20))
    assert len(daily.records) == 10_746
    assert len(daily.by_norad) == len(daily.records)


@requires_archive
def test_the_one_known_malformed_record_in_the_corpus():
    """2026-05-28 holds the corpus's only bad record: a 70-character line 1.

    ``-66000-10`` needs a two-digit BSTAR exponent and the fixed-width
    format has room for one, so the checksum is pushed out of column 69.
    Quarantining one satellite must not cost the other 10,397.
    """
    archive = TleArchive(_ARCHIVE_ROOT)
    daily = archive.load(dt.date(2026, 5, 28))
    assert len(daily.quarantined) == 1
    assert len(daily.records) == 10_397
    assert daily.malformed_fraction < MAX_MALFORMED_RECORD_FRACTION
    (bad,) = daily.quarantined
    assert len(bad.line1) == 70
    assert "-66000-10" in bad.line1
    assert "checksum" in bad.reason


@requires_archive
def test_manifest_rows_report_the_quarantine_count():
    archive = TleArchive(_ARCHIVE_ROOT)
    rows = archive.manifest_rows([dt.date(2026, 5, 28), dt.date(2026, 8, 20)])
    by_file = {row["file"]: row for row in rows}
    assert by_file["starlink_20260528.tle"]["quarantined"] == "1"
    assert by_file["starlink_20260820.tle"]["quarantined"] == "0"
