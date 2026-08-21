"""TLE parsing, daily-file catalogues, and the file-set freeze (SDD F3).

Data: ``~/demo/tle_data/starlink/tle/starlink_YYYYMMDD.tle``, 373 daily
files covering 2025-07-27 … 2026-08-20, three-line format
(name, line 1, line 2).

Two facts about this corpus drive the design, both measured rather than
assumed (see ``docs/EPHEMERIS-NOTES.md``):

1. A daily file is **not** a set of same-day epochs.  ``starlink_20260820``
   spans 21 days of epochs; only 97% are within 24 h of that date's 00:00
   UTC, dropping to 64% by the following midnight.  So SDD F3's "nearest
   epoch, age ≤ 24 h" has to be a *selection over a window of files*, not a
   whole-file load.
2. Records are one-per-NORAD within a file (10,746 unique ids, zero
   duplicates in the sampled file), so a per-file dict is lossless.

Malformed records are **quarantined, not ignored and not repaired**: the
record is dropped, recorded with its reason, and the load fails outright if
the malformed fraction of a file exceeds ``MAX_MALFORMED_RECORD_FRACTION``.
Silently skipping would shrink the constellation invisibly; failing the
whole day over one bad line would throw away 10,745 good satellites.

Measured over the entire corpus (373 files, 3,545,756 records): **one**
malformed record, in ``starlink_20260528.tle``.  Its line 1 is 70 characters
because the BSTAR field ``-66000-10`` needs a two-digit exponent and the
fixed-width format has room for one, which pushes the checksum out of
column 69.  That is an upstream defect; repairing it here would be inventing
data.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..errors import MCRLContractError

_FILENAME_RE = re.compile(r"^starlink_(\d{8})\.tle$")


MAX_MALFORMED_RECORD_FRACTION: float = 1e-3
"""**S** — ceiling on quarantined records per daily file.

Chosen from the two regimes it has to separate, not from the corpus rate.
The worst real file holds one bad record out of 10,398, i.e. 9.6e-4 — so a
1e-4 ceiling would reject that whole day over a single upstream typo, while
a misaligned or truncated file quarantines ~100% of its records and fails
1e-3 by three orders of magnitude.  1e-3 tolerates roughly ten bad records
in a full-size file and nothing structural.

It also keeps small inputs strict: any single bad record in a handful-sized
file is far above 1e-3, so unit-test fixtures still fail loudly.
"""


class TleFormatError(MCRLContractError):
    """A TLE line is malformed, mis-numbered, or fails its checksum."""


class TleQuarantineError(MCRLContractError):
    """Too many records in one file had to be quarantined."""


@dataclass(frozen=True)
class QuarantinedRecord:
    """A record that could not be parsed, kept for the audit trail."""

    index: int
    reason: str
    name: str
    line1: str
    line2: str


@dataclass(frozen=True)
class TleRecord:
    """One three-line TLE entry."""

    norad_id: int
    name: str
    line1: str
    line2: str
    epoch_utc: dt.datetime

    def age_seconds(self, when: dt.datetime) -> float:
        """Absolute age of this element set relative to ``when``."""
        return abs((when - self.epoch_utc).total_seconds())


def tle_checksum(line: str) -> int:
    """Modulo-10 checksum over the first 68 columns (digits, minus = 1)."""
    total = 0
    for char in line[:68]:
        if char.isdigit():
            total += int(char)
        elif char == "-":
            total += 1
    return total % 10


def _validate_line(line: str, *, expected_number: int, source: str) -> str:
    if len(line) < 69:
        raise TleFormatError(
            f"{source}: line {expected_number} is {len(line)} chars, need ≥ 69"
        )
    if line[0] != str(expected_number):
        raise TleFormatError(
            f"{source}: expected line number {expected_number}, got {line[0]!r}"
        )
    stated = line[68]
    if not stated.isdigit():
        raise TleFormatError(f"{source}: checksum column is {stated!r}")
    actual = tle_checksum(line)
    if int(stated) != actual:
        raise TleFormatError(
            f"{source}: line {expected_number} checksum {stated} != {actual}"
        )
    return line


def parse_epoch(line1: str) -> dt.datetime:
    """Decode columns 19-32 (``YYDDD.DDDDDDDD``) into a UTC datetime."""
    two_digit_year = int(line1[18:20])
    day_of_year = float(line1[20:32])
    # TLE century rule: 57-99 -> 19xx, 00-56 -> 20xx.
    year = 2000 + two_digit_year if two_digit_year < 57 else 1900 + two_digit_year
    return dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc) + dt.timedelta(
        days=day_of_year - 1.0
    )


def parse_tle_text(
    text: str, *, source: str = "<text>"
) -> tuple[list[TleRecord], list[QuarantinedRecord]]:
    """Parse three-line-format TLE text.

    Returns ``(records, quarantined)``.  A file whose line count is not a
    multiple of three is a structural failure and still raises: that is a
    truncated or misaligned file, not one bad satellite.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) % 3 != 0:
        raise TleFormatError(
            f"{source}: {len(lines)} non-blank lines is not a multiple of 3"
        )
    records: list[TleRecord] = []
    quarantined: list[QuarantinedRecord] = []
    for index in range(0, len(lines), 3):
        name = lines[index].strip()
        raw1, raw2 = lines[index + 1], lines[index + 2]
        try:
            line1 = _validate_line(
                raw1, expected_number=1, source=f"{source}#{index}"
            )
            line2 = _validate_line(
                raw2, expected_number=2, source=f"{source}#{index}"
            )
            norad_1 = int(line1[2:7])
            norad_2 = int(line2[2:7])
            if norad_1 != norad_2:
                raise TleFormatError(
                    f"{source}#{index}: NORAD id mismatch {norad_1} != {norad_2}"
                )
            epoch = parse_epoch(line1)
        except (TleFormatError, ValueError) as error:
            quarantined.append(
                QuarantinedRecord(
                    index=index,
                    reason=str(error),
                    name=name,
                    line1=raw1,
                    line2=raw2,
                )
            )
            continue
        records.append(
            TleRecord(
                norad_id=norad_1,
                name=name,
                line1=line1,
                line2=line2,
                epoch_utc=epoch,
            )
        )
    return records, quarantined


@dataclass(frozen=True)
class TleDailyFile:
    """One daily file plus the hash that freezes it (SDD F3, §7.1)."""

    path: Path
    file_date: dt.date
    sha256: str
    records: tuple[TleRecord, ...]
    quarantined: tuple[QuarantinedRecord, ...] = ()

    @property
    def by_norad(self) -> dict[int, TleRecord]:
        return {record.norad_id: record for record in self.records}

    @property
    def malformed_fraction(self) -> float:
        total = len(self.records) + len(self.quarantined)
        return len(self.quarantined) / total if total else 0.0

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        max_malformed_fraction: float = MAX_MALFORMED_RECORD_FRACTION,
    ) -> TleDailyFile:
        path = Path(path)
        if not path.is_file():
            raise MCRLContractError(f"TLE file not found: {path}")
        match = _FILENAME_RE.match(path.name)
        if match is None:
            raise MCRLContractError(
                f"TLE filename does not match starlink_YYYYMMDD.tle: {path.name}"
            )
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        records, quarantined = parse_tle_text(
            raw.decode("utf-8"), source=path.name
        )
        total = len(records) + len(quarantined)
        if total and len(quarantined) / total > max_malformed_fraction:
            raise TleQuarantineError(
                f"{path.name}: {len(quarantined)} of {total} records malformed "
                f"({len(quarantined) / total:.2e} > {max_malformed_fraction:.2e}); "
                f"first reason: {quarantined[0].reason}"
            )
        seen: set[int] = set()
        for record in records:
            if record.norad_id in seen:
                raise TleFormatError(
                    f"{path.name}: duplicate NORAD id {record.norad_id}"
                )
            seen.add(record.norad_id)
        return cls(
            path=path,
            file_date=dt.datetime.strptime(match.group(1), "%Y%m%d").date(),
            sha256=digest,
            records=tuple(records),
            quarantined=tuple(quarantined),
        )


class TleArchive:
    """The directory of daily files, indexed by date.

    Loading is lazy and cached: a probe that walks 30 simulation dates
    touches 30 files, not 373.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()
        if not self.root.is_dir():
            raise MCRLContractError(f"TLE root is not a directory: {self.root}")
        self._paths: dict[dt.date, Path] = {}
        for path in sorted(self.root.iterdir()):
            match = _FILENAME_RE.match(path.name)
            if match is None:
                continue
            file_date = dt.datetime.strptime(match.group(1), "%Y%m%d").date()
            self._paths[file_date] = path
        if not self._paths:
            raise MCRLContractError(f"no starlink_*.tle files under {self.root}")
        self._cache: dict[dt.date, TleDailyFile] = {}

    @property
    def dates(self) -> tuple[dt.date, ...]:
        return tuple(sorted(self._paths))

    @property
    def date_range(self) -> tuple[dt.date, dt.date]:
        dates = self.dates
        return dates[0], dates[-1]

    def has(self, file_date: dt.date) -> bool:
        return file_date in self._paths

    def load(self, file_date: dt.date) -> TleDailyFile:
        if file_date not in self._paths:
            first, last = self.date_range
            raise MCRLContractError(
                f"no TLE file for {file_date}; archive covers {first}..{last}"
            )
        cached = self._cache.get(file_date)
        if cached is None:
            cached = TleDailyFile.load(self._paths[file_date])
            self._cache[file_date] = cached
        return cached

    def manifest_rows(self, file_dates: list[dt.date]) -> list[dict[str, str]]:
        """Per-file freeze rows: name, date, sha256, record count."""
        rows = []
        for file_date in sorted(set(file_dates)):
            daily = self.load(file_date)
            rows.append(
                {
                    "file": daily.path.name,
                    "date": daily.file_date.isoformat(),
                    "sha256": daily.sha256,
                    "records": str(len(daily.records)),
                    "quarantined": str(len(daily.quarantined)),
                }
            )
        return rows
