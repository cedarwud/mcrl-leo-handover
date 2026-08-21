"""Real-TLE + SGP4 ephemeris layer (SDD §3.1, W-02).

Replaces the synthetic Walker constellation of
``family_b_geometry.propagate_ecef`` with real Starlink elements.

What this layer owns
--------------------
* the element-selection policy of SDD F3 (nearest epoch, age ≤ 24 h);
* the train/test date split — block-alternating with an embargo gap, which
  keeps the corpus's growth and altitude trends off the train/test axis
  while staying far enough apart in time that no pass geometry is shared;
* SGP4 propagation and the TEME→ECEF rotation;
* look angles (slant range, elevation, off-nadir) against the service area;
* the freeze manifest §7.1 demands before the first probe runs.

What it does **not** own: D2 selection (W-04), dwell (W-05), beams and link
budget (W-06).  Those consume ``look_angles`` output.

Altitude is now an observation, not a parameter — see
``constants.TABLE_I_ALTITUDE_KM``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Protocol, Sequence

import numpy as np
from sgp4.api import SGP4_ERRORS, Satrec, SatrecArray, WGS72, accelerated

from ..errors import MCRLContractError
from .constants import (
    AREA_CENTER_LAT_DEG,
    AREA_CENTER_LON_DEG,
    MAX_TLE_AGE_H,
    R_E_KM,
    SGP4_GRAVITY_MODEL,
    TIME_STEP_S,
    TLE_ROOT_DEFAULT,
)
from .geometry import (
    geodetic_to_ecef,
    gmst_rad,
    julian_date,
    look_angles,
    range_rate_km_s,
    teme_to_ecef,
    teme_velocity_to_ecef,
)
from .tle import TleArchive, TleRecord


class EphemerisError(MCRLContractError):
    """SGP4 refused to propagate, or the element selection came up empty."""


# ---------------------------------------------------------------------------
# Element selection (SDD F3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ElementSelection:
    """The elements chosen for one simulation start, plus the audit trail."""

    when_utc: dt.datetime
    records: tuple[TleRecord, ...]
    source_dates: tuple[dt.date, ...]
    max_age_h: float
    considered_norads: int
    rejected_stale: int

    @property
    def ages_h(self) -> np.ndarray:
        return np.array(
            [record.age_seconds(self.when_utc) / 3600.0 for record in self.records],
            dtype=np.float64,
        )

    def age_summary(self) -> dict[str, float]:
        ages = self.ages_h
        if ages.size == 0:
            return {"count": 0.0}
        return {
            "count": float(ages.size),
            "min_h": float(ages.min()),
            "p50_h": float(np.percentile(ages, 50)),
            "p95_h": float(np.percentile(ages, 95)),
            "max_h": float(ages.max()),
        }


def select_elements(
    archive: TleArchive,
    when_utc: dt.datetime,
    *,
    max_age_h: float = MAX_TLE_AGE_H,
    search_days: int = 1,
) -> ElementSelection:
    """SDD F3: per NORAD id take the nearest epoch, then drop age > max.

    ``search_days`` widens the file window around ``when_utc``'s date.  It
    is needed, not cosmetic: a single daily file spans ~21 days of epochs
    and its 24 h coverage falls from 97% to 64% across the day it is named
    after, so "nearest epoch" has to look at neighbouring files too.

    Age is **absolute** ``|epoch − when|``, which permits a few hours of
    backward extrapolation.  SGP4 is symmetric in Δt and the alternative
    (past-only) would systematically double the mean age.  Declared as an
    **S**-level choice.
    """
    if when_utc.tzinfo is None:
        raise ValueError("when_utc must be timezone-aware")
    if search_days < 0:
        raise ValueError("search_days must be >= 0")
    when_utc = when_utc.astimezone(dt.timezone.utc)

    center = when_utc.date()
    source_dates = [
        center + dt.timedelta(days=offset)
        for offset in range(-search_days, search_days + 1)
        if archive.has(center + dt.timedelta(days=offset))
    ]
    if not source_dates:
        raise EphemerisError(
            f"no TLE file within ±{search_days} d of {center}"
        )

    best: dict[int, TleRecord] = {}
    for file_date in source_dates:
        for record in archive.load(file_date).records:
            incumbent = best.get(record.norad_id)
            if incumbent is None or record.age_seconds(when_utc) < incumbent.age_seconds(
                when_utc
            ):
                best[record.norad_id] = record

    max_age_s = max_age_h * 3600.0
    fresh = [
        record
        for _, record in sorted(best.items())
        if record.age_seconds(when_utc) <= max_age_s
    ]
    if not fresh:
        raise EphemerisError(
            f"no element set within {max_age_h} h of {when_utc.isoformat()}"
        )
    return ElementSelection(
        when_utc=when_utc,
        records=tuple(fresh),
        source_dates=tuple(source_dates),
        max_age_h=max_age_h,
        considered_norads=len(best),
        rejected_stale=len(best) - len(fresh),
    )


# ---------------------------------------------------------------------------
# Train/test date split (SDD F3, revised 2026-08-22 by author ruling)
# ---------------------------------------------------------------------------

TRAIN = "train"
TEST = "test"
EMBARGO = "embargo"
SPLIT_PARTS = (TRAIN, TEST)


class Split(Protocol):
    """What the sampler and the freeze manifest need from any split."""

    def available_dates(
        self, archive: TleArchive, part: str
    ) -> tuple[dt.date, ...]: ...

    def as_dict(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class BlockAlternatingSplit:
    """Alternating date blocks with an embargo gap.  **The frozen scheme.**

    F3 originally said "split by date range, do not interleave".  W-02
    measured what a single contiguous cut costs: the constellation grows
    ~25% across the corpus and the visible-satellite altitude drifts down
    from ~540 km to ~485 km, so a chronological split hands test a
    systematically larger and lower constellation than train.  **Two
    distribution shifts, both in the same direction.**

    Author ruling (2026-08-22): there is a third option rather than a
    choice between leakage and shift.  Alternate fixed-length blocks
    between train and test, and leave an embargo gap between every pair of
    adjacent blocks::

        |<- 7 d train ->|1 d|<- 7 d test ->|1 d| 7 d train | ... 

    The growth and altitude trends then average out on both sides, while
    the embargo keeps the two halves far enough apart in time that they
    cannot share pass geometry.  One embargo day puts the nearest train and
    test dates two days apart — vastly more than the 10 s episode and more
    than the ground-track repeat of any Starlink shell, whereas the leak F3
    was guarding against was episodes *minutes* apart.

    ``block_days`` and ``embargo_days`` are **S**-level and must be frozen
    in the W-13 PREREG.
    """

    first_date: dt.date
    last_date: dt.date
    block_days: int = 7
    embargo_days: int = 1
    first_block_part: str = TRAIN

    def __post_init__(self) -> None:
        if self.first_date > self.last_date:
            raise ValueError("date range is inverted")
        if self.block_days < 1:
            raise ValueError("block_days must be >= 1")
        if self.embargo_days < 1:
            raise MCRLContractError(
                "embargo_days must be >= 1; a zero embargo puts adjacent "
                "train and test days next to each other"
            )
        if self.first_block_part not in SPLIT_PARTS:
            raise ValueError(f"unknown part {self.first_block_part!r}")

    @classmethod
    def for_archive(
        cls,
        archive: TleArchive,
        *,
        block_days: int = 7,
        embargo_days: int = 1,
        first_block_part: str = TRAIN,
    ) -> BlockAlternatingSplit:
        first, last = archive.date_range
        return cls(
            first_date=first,
            last_date=last,
            block_days=block_days,
            embargo_days=embargo_days,
            first_block_part=first_block_part,
        )

    @property
    def cycle_days(self) -> int:
        return 2 * (self.block_days + self.embargo_days)

    def _other_part(self) -> str:
        return TEST if self.first_block_part == TRAIN else TRAIN

    def part_for(self, date: dt.date) -> str:
        """``"train"``, ``"test"``, or ``"embargo"`` for one calendar date."""
        if not self.first_date <= date <= self.last_date:
            raise MCRLContractError(f"{date} is outside the split range")
        position = (date - self.first_date).days % self.cycle_days
        if position < self.block_days:
            return self.first_block_part
        if position < self.block_days + self.embargo_days:
            return EMBARGO
        if position < 2 * self.block_days + self.embargo_days:
            return self._other_part()
        return EMBARGO

    def available_dates(
        self, archive: TleArchive, part: str
    ) -> tuple[dt.date, ...]:
        if part not in SPLIT_PARTS:
            raise ValueError(f"unknown split part {part!r}")
        return tuple(
            date
            for date in archive.dates
            if self.first_date <= date <= self.last_date
            and self.part_for(date) == part
        )

    def embargoed_dates(self, archive: TleArchive) -> tuple[dt.date, ...]:
        return tuple(
            date for date in archive.dates if self.part_for(date) == EMBARGO
        )

    def minimum_gap_days(self, archive: TleArchive) -> int:
        """Smallest calendar distance between any train date and any test date."""
        train = self.available_dates(archive, TRAIN)
        test = self.available_dates(archive, TEST)
        if not train or not test:
            raise MCRLContractError("one side of the split is empty")
        merged = sorted(
            [(date, TRAIN) for date in train] + [(date, TEST) for date in test]
        )
        gap = min(
            (later[0] - earlier[0]).days
            for earlier, later in zip(merged, merged[1:])
            if earlier[1] != later[1]
        )
        return int(gap)

    def as_dict(self) -> dict[str, object]:
        return {
            "scheme": "block-alternating-with-embargo",
            "first_date": self.first_date.isoformat(),
            "last_date": self.last_date.isoformat(),
            "block_days": self.block_days,
            "embargo_days": self.embargo_days,
            "first_block_part": self.first_block_part,
            "cycle_days": self.cycle_days,
        }


@dataclass(frozen=True)
class ContiguousDateSplit:
    """One chronological cut: train early, test late.  **Superseded.**

    Retained only so the distribution shift that motivated
    :class:`BlockAlternatingSplit` stays reproducible
    (``tests/test_w02_ephemeris.py``).  Do not use it for a live run.
    """

    train_start: dt.date
    train_end: dt.date
    test_start: dt.date
    test_end: dt.date

    def __post_init__(self) -> None:
        if self.train_start > self.train_end:
            raise ValueError("train range is inverted")
        if self.test_start > self.test_end:
            raise ValueError("test range is inverted")
        if not (self.train_end < self.test_start or self.test_end < self.train_start):
            raise MCRLContractError(
                "train and test date ranges overlap; SDD F3 forbids interleaving"
            )

    @classmethod
    def chronological(
        cls,
        archive: TleArchive,
        *,
        test_fraction: float = 0.2,
    ) -> ContiguousDateSplit:
        dates = archive.dates
        if len(dates) < 2:
            raise MCRLContractError("need at least two dates to split")
        if not 0.0 < test_fraction < 1.0:
            raise ValueError("test_fraction must be in (0,1)")
        cut = len(dates) - max(1, int(round(len(dates) * test_fraction)))
        cut = min(max(cut, 1), len(dates) - 1)
        return cls(
            train_start=dates[0],
            train_end=dates[cut - 1],
            test_start=dates[cut],
            test_end=dates[-1],
        )

    def dates_for(self, part: str) -> tuple[dt.date, dt.date]:
        if part == TRAIN:
            return self.train_start, self.train_end
        if part == TEST:
            return self.test_start, self.test_end
        raise ValueError(f"unknown split part {part!r}")

    def available_dates(
        self, archive: TleArchive, part: str
    ) -> tuple[dt.date, ...]:
        first, last = self.dates_for(part)
        return tuple(date for date in archive.dates if first <= date <= last)

    def as_dict(self) -> dict[str, object]:
        return {
            "scheme": "contiguous-chronological-SUPERSEDED",
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
        }


@dataclass(frozen=True)
class EpisodeStartSampler:
    """Draws episode start times inside one part of a split.

    **S**-level sampling distribution (F3 requires it to be frozen):
    date uniform over the part's **available** file dates, time-of-day
    uniform over the 86,400 s of that date, snapped down to a whole
    ``time_step_s``.

    "Available", not "calendar range": the corpus is 373 files across a
    390-day span, so 17 dates have no file.  Drawing over the calendar
    range would put ~4% of episodes on a date whose elements have to come
    from a neighbouring file — a silent, undeclared change of the age
    distribution.  Drawing over the file list keeps the sampling
    distribution equal to the thing that was actually frozen.
    """

    part: str
    available_dates: tuple[dt.date, ...]
    time_step_s: float = TIME_STEP_S

    def __post_init__(self) -> None:
        if self.part not in SPLIT_PARTS:
            raise ValueError(f"unknown split part {self.part!r}")
        if not self.available_dates:
            raise MCRLContractError(f"no available dates for part {self.part!r}")
        if list(self.available_dates) != sorted(set(self.available_dates)):
            raise MCRLContractError("available_dates must be sorted and unique")

    @classmethod
    def for_archive(
        cls,
        archive: TleArchive,
        split: Split,
        part: str,
        *,
        time_step_s: float = TIME_STEP_S,
    ) -> EpisodeStartSampler:
        return cls(part, split.available_dates(archive, part), time_step_s)

    def draw(self, rng: np.random.Generator) -> dt.datetime:
        day = self.available_dates[int(rng.integers(0, len(self.available_dates)))]
        second_of_day = float(rng.integers(0, 86_400))
        snapped = np.floor(second_of_day / self.time_step_s) * self.time_step_s
        return dt.datetime.combine(
            day, dt.time(0, 0), tzinfo=dt.timezone.utc
        ) + dt.timedelta(seconds=float(snapped))

    def as_dict(self) -> dict[str, object]:
        first, last = self.available_dates[0], self.available_dates[-1]
        return {
            "part": self.part,
            "date_first": first.isoformat(),
            "date_last": last.isoformat(),
            "date_count": len(self.available_dates),
            "calendar_span_days": (last - first).days + 1,
            "date_distribution": "uniform over available file dates",
            "time_of_day_distribution": (
                f"uniform over [0, 86400) s, floor-snapped to {self.time_step_s} s"
            ),
        }


# ---------------------------------------------------------------------------
# Propagation
# ---------------------------------------------------------------------------


def step_times(
    start_utc: dt.datetime,
    num_steps: int,
    *,
    time_step_s: float = TIME_STEP_S,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(jd, fr)`` arrays for ``num_steps`` slots from ``start_utc``.

    The Julian day stays fixed and only the fraction advances, which keeps
    a 1 s step from being rounded away inside a 2.46e6-sized float.
    """
    if num_steps < 1:
        raise ValueError("num_steps must be >= 1")
    jd0, fr0 = julian_date(start_utc)
    offsets = np.arange(num_steps, dtype=np.float64) * (time_step_s / 86400.0)
    return np.full(num_steps, jd0, dtype=np.float64), fr0 + offsets


class SatelliteSet:
    """A frozen set of element sets, ready to propagate."""

    def __init__(self, records: Sequence[TleRecord]) -> None:
        if not records:
            raise EphemerisError("SatelliteSet needs at least one record")
        if SGP4_GRAVITY_MODEL != "wgs72":
            raise MCRLContractError(
                f"TLEs require WGS-72; constants say {SGP4_GRAVITY_MODEL!r}"
            )
        self.records: tuple[TleRecord, ...] = tuple(records)
        self._satrecs = [
            Satrec.twoline2rv(record.line1, record.line2, WGS72)
            for record in self.records
        ]
        self._array = SatrecArray(self._satrecs)

    def __len__(self) -> int:
        return len(self.records)

    @property
    def norad_ids(self) -> np.ndarray:
        return np.array(
            [record.norad_id for record in self.records], dtype=np.int64
        )

    def subset(self, indices: Iterable[int]) -> SatelliteSet:
        return SatelliteSet([self.records[int(i)] for i in indices])

    def propagate_teme(
        self, jd: np.ndarray, fr: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(error_codes (S,T), r_teme (S,T,3) km, v (S,T,3) km/s)``."""
        jd = np.asarray(jd, dtype=np.float64)
        fr = np.asarray(fr, dtype=np.float64)
        if jd.shape != fr.shape or jd.ndim != 1:
            raise ValueError("jd and fr must be 1-D arrays of equal length")
        codes, r, v = self._array.sgp4(jd, fr)
        return codes, r, v

    def propagate_ecef(
        self,
        jd: np.ndarray,
        fr: np.ndarray,
        *,
        require_all_healthy: bool = True,
    ) -> np.ndarray:
        """Return ECEF positions ``(S,T,3)`` in km.

        Fail-loud by default: any SGP4 error code aborts.  A decayed or
        otherwise unpropagatable satellite silently returning NaN would
        flow straight into elevation, D2 margin, and the mask.
        """
        codes, r_teme, _v = self.propagate_teme(jd, fr)
        if require_all_healthy and bool(np.any(codes != 0)):
            self._raise_for_codes(codes)
        return teme_to_ecef(r_teme, self._gmst(jd, fr))

    def propagate_ecef_state(
        self,
        jd: np.ndarray,
        fr: np.ndarray,
        *,
        require_all_healthy: bool = True,
    ) -> tuple[np.ndarray, np.ndarray]:
        """ECEF position and velocity, both ``(S,T,3)``, km and km/s.

        The velocity is in the **rotating** frame, so a range rate computed
        against a fixed ground point needs no further correction.
        """
        codes, r_teme, v_teme = self.propagate_teme(jd, fr)
        if require_all_healthy and bool(np.any(codes != 0)):
            self._raise_for_codes(codes)
        gmst = self._gmst(jd, fr)
        r_ecef = teme_to_ecef(r_teme, gmst)
        v_ecef = teme_velocity_to_ecef(v_teme, r_ecef, gmst)
        return r_ecef, v_ecef

    def _gmst(self, jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
        return np.array(
            [gmst_rad(float(j), float(f)) for j, f in zip(jd, fr)],
            dtype=np.float64,
        )

    def _raise_for_codes(self, codes: np.ndarray) -> None:
        bad = np.argwhere(codes != 0)
        first_sat, first_t = int(bad[0][0]), int(bad[0][1])
        code = int(codes[first_sat, first_t])
        raise EphemerisError(
            f"SGP4 error {code} ({SGP4_ERRORS.get(code, 'unknown')}) for "
            f"NORAD {self.records[first_sat].norad_id} at step {first_t}; "
            f"{int(np.count_nonzero(np.any(codes != 0, axis=1)))} of "
            f"{len(self)} satellites affected"
        )

    def healthy_indices(self, jd: np.ndarray, fr: np.ndarray) -> np.ndarray:
        """Indices whose propagation succeeds at every requested time."""
        codes, _r, _v = self.propagate_teme(jd, fr)
        return np.flatnonzero(~np.any(codes != 0, axis=1))


# ---------------------------------------------------------------------------
# Visibility against the service area
# ---------------------------------------------------------------------------


def service_area_center_ecef() -> np.ndarray:
    """ECEF position of the MODQN §IV service-area centre."""
    return geodetic_to_ecef(AREA_CENTER_LAT_DEG, AREA_CENTER_LON_DEG)


@dataclass(frozen=True)
class VisibilityScan:
    """Look angles for every satellite at every requested time."""

    norad_ids: np.ndarray
    slant_range_km: np.ndarray
    elevation_deg: np.ndarray
    off_nadir_deg: np.ndarray
    altitude_km: np.ndarray

    def visible(self, min_elevation_deg: float) -> np.ndarray:
        return self.elevation_deg >= min_elevation_deg

    def ever_visible_indices(self, min_elevation_deg: float) -> np.ndarray:
        return np.flatnonzero(np.any(self.visible(min_elevation_deg), axis=1))


def scan_visibility(
    satellites: SatelliteSet,
    jd: np.ndarray,
    fr: np.ndarray,
    *,
    ground_ecef_km: np.ndarray | None = None,
    require_all_healthy: bool = False,
) -> VisibilityScan:
    """Propagate and reduce to look angles at one ground point."""
    ground = (
        service_area_center_ecef() if ground_ecef_km is None else ground_ecef_km
    )
    sat_ecef = satellites.propagate_ecef(
        jd, fr, require_all_healthy=require_all_healthy
    )
    slant, elevation, off_nadir = look_angles(sat_ecef, ground)
    altitude = np.linalg.norm(sat_ecef, axis=-1) - R_E_KM
    return VisibilityScan(
        norad_ids=satellites.norad_ids,
        slant_range_km=slant,
        elevation_deg=elevation,
        off_nadir_deg=off_nadir,
        altitude_km=altitude,
    )


def shortlist_visible(
    satellites: SatelliteSet,
    start_utc: dt.datetime,
    *,
    duration_s: float,
    coarse_step_s: float,
    min_elevation_deg: float,
    ground_ecef_km: np.ndarray | None = None,
    elevation_margin_deg: float = 5.0,
) -> np.ndarray:
    """Cheap pre-filter: which satellites come near the horizon at all.

    Propagating ~10,000 satellites at 1 s over a long horizon is hundreds of
    megabytes; a coarse scan plus a margin cuts that to the handful that
    matter.  The margin covers what a satellite can traverse between coarse
    samples (LEO ground track ≈ 7 km/s → ~0.06°/s of elevation near zenith).
    """
    if coarse_step_s <= 0.0:
        raise ValueError("coarse_step_s must be positive")
    num = max(int(np.ceil(duration_s / coarse_step_s)) + 1, 2)
    jd, fr = step_times(start_utc, num, time_step_s=coarse_step_s)
    healthy = satellites.healthy_indices(jd, fr)
    if healthy.size == 0:
        return healthy
    healthy_set = satellites.subset(healthy)
    scan = scan_visibility(
        healthy_set, jd, fr, ground_ecef_km=ground_ecef_km
    )
    near = scan.ever_visible_indices(min_elevation_deg - elevation_margin_deg)
    return healthy[near]


# ---------------------------------------------------------------------------
# Freeze manifest (SDD §3.1 "必須凍結", §7.1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EphemerisConfig:
    """Everything the ephemeris layer must have frozen before probe P1."""

    tle_root: str = TLE_ROOT_DEFAULT
    time_step_s: float = TIME_STEP_S
    max_tle_age_h: float = MAX_TLE_AGE_H
    epoch_search_days: int = 1
    gravity_model: str = SGP4_GRAVITY_MODEL
    min_elevation_deg: float = 10.0
    """**S** — screening floor only.  Service eligibility is D2's call (W-04)."""

    def archive(self) -> TleArchive:
        return TleArchive(self.tle_root)

    def as_dict(self) -> dict[str, object]:
        return {
            "tle_root": str(Path(self.tle_root).expanduser()),
            "time_step_s": self.time_step_s,
            "max_tle_age_h": self.max_tle_age_h,
            "epoch_search_days": self.epoch_search_days,
            "gravity_model": self.gravity_model,
            "min_elevation_deg": self.min_elevation_deg,
        }


def file_set_hash(rows: Sequence[dict[str, str]]) -> str:
    """One hash over the whole frozen file set (name + sha256, sorted)."""
    joined = "\n".join(
        f"{row['file']}:{row['sha256']}" for row in sorted(rows, key=lambda r: r["file"])
    )
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def build_freeze_manifest(
    config: EphemerisConfig,
    split: Split,
    *,
    sampled_dates: Sequence[dt.date] | None = None,
    start_utc: dt.datetime | None = None,
) -> dict[str, object]:
    """Assemble the §7.1 ephemeris freeze record.

    ``sampled_dates`` defaults to every date in the archive, i.e. the
    whole corpus is frozen.  Pass a subset only when the PREREG commits to
    that subset.
    """
    import sgp4

    archive = config.archive()
    dates = list(sampled_dates) if sampled_dates is not None else list(archive.dates)
    rows = archive.manifest_rows(dates)
    first, last = archive.date_range
    present = set(archive.dates)
    missing = [
        (first + dt.timedelta(days=offset)).isoformat()
        for offset in range((last - first).days + 1)
        if (first + dt.timedelta(days=offset)) not in present
    ]
    manifest: dict[str, object] = {
        "schema": "mcrl-ephemeris-freeze-v1",
        "config": config.as_dict(),
        "archive": {
            "date_first": first.isoformat(),
            "date_last": last.isoformat(),
            "file_count": len(archive.dates),
            "calendar_span_days": (last - first).days + 1,
            "missing_dates": missing,
        },
        "frozen_files": rows,
        "file_set_sha256": file_set_hash(rows),
        "split": split.as_dict(),
        "sampling": {
            part: EpisodeStartSampler.for_archive(
                archive, split, part, time_step_s=config.time_step_s
            ).as_dict()
            for part in SPLIT_PARTS
        },
        "sgp4": {
            "version": sgp4.__version__,
            "accelerated": bool(accelerated),
            "gravity_model": config.gravity_model,
        },
    }
    if isinstance(split, BlockAlternatingSplit):
        manifest["split"] = dict(split.as_dict()) | {
            "train_files": len(split.available_dates(archive, TRAIN)),
            "test_files": len(split.available_dates(archive, TEST)),
            "embargoed_files": len(split.embargoed_dates(archive)),
            "minimum_train_test_gap_days": split.minimum_gap_days(archive),
        }
    if start_utc is not None:
        selection = select_elements(
            archive,
            start_utc,
            max_age_h=config.max_tle_age_h,
            search_days=config.epoch_search_days,
        )
        manifest["start_utc"] = start_utc.astimezone(dt.timezone.utc).isoformat()
        manifest["element_selection"] = {
            "source_dates": [d.isoformat() for d in selection.source_dates],
            "considered_norads": selection.considered_norads,
            "selected": len(selection.records),
            "rejected_stale": selection.rejected_stale,
            "age_hours": selection.age_summary(),
        }
    return manifest


def write_freeze_manifest(path: str | Path, manifest: dict[str, object]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path
