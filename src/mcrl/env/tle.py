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

Everything is fail-loud: a malformed line, a bad checksum, or a missing
file raises rather than silently shrinking the constellation.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from ..errors import MCRLContractError

_FILENAME_RE = re.compile(r"^starlink_(\d{8})\.tle$")


class TleFormatError(MCRLContractError):
    """A TLE line is malformed, mis-numbered, or fails its checksum."""


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


def parse_tle_text(text: str, *, source: str = "<text>") -> list[TleRecord]:
    """Parse three-line-format TLE text into records."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) % 3 != 0:
        raise TleFormatError(
            f"{source}: {len(lines)} non-blank lines is not a multiple of 3"
        )
    records: list[TleRecord] = []
    for index in range(0, len(lines), 3):
        name = lines[index].strip()
        line1 = _validate_line(
            lines[index + 1], expected_number=1, source=f"{source}#{index}"
        )
        line2 = _validate_line(
            lines[index + 2], expected_number=2, source=f"{source}#{index}"
        )
        norad_1 = int(line1[2:7])
        norad_2 = int(line2[2:7])
        if norad_1 != norad_2:
            raise TleFormatError(
                f"{source}#{index}: NORAD id mismatch {norad_1} != {norad_2}"
            )
        records.append(
            TleRecord(
                norad_id=norad_1,
                name=name,
                line1=line1,
                line2=line2,
                epoch_utc=parse_epoch(line1),
            )
        )
    return records


@dataclass(frozen=True)
class TleDailyFile:
    """One daily file plus the hash that freezes it (SDD F3, §7.1)."""

    path: Path
    file_date: dt.date
    sha256: str
    records: tuple[TleRecord, ...]

    @property
    def by_norad(self) -> dict[int, TleRecord]:
        return {record.norad_id: record for record in self.records}

    @classmethod
    def load(cls, path: str | Path) -> TleDailyFile:
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
        records = parse_tle_text(raw.decode("utf-8"), source=path.name)
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
                }
            )
        return rows
