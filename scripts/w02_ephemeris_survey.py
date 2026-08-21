"""Measure what the real TLE corpus actually gives at the service area.

Not a probe (probes are W-11 and answer pre-registered questions).  This is
the data-property survey W-02 needs so the numbers quoted in
``docs/EPHEMERIS-NOTES.md`` are measured rather than assumed.

    .venv/bin/python scripts/w02_ephemeris_survey.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcrl.env.constants import R_E_KM, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    DateSplit,
    SatelliteSet,
    scan_visibility,
    select_elements,
    step_times,
)
from mcrl.env.geometry import horizon_off_nadir_deg  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402

SAMPLE_STARTS = [
    dt.datetime(2025, 8, 15, 3, 0, tzinfo=dt.timezone.utc),
    dt.datetime(2025, 12, 3, 11, 30, tzinfo=dt.timezone.utc),
    dt.datetime(2026, 4, 9, 18, 45, tzinfo=dt.timezone.utc),
    dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc),
]
ELEVATION_MASKS = (10.0, 15.0, 25.0, 40.0)


def _pct(values: np.ndarray, q: float) -> float:
    return float(np.percentile(values, q))


def main() -> None:
    archive = TleArchive(TLE_ROOT_DEFAULT)
    first, last = archive.date_range
    present = set(archive.dates)
    missing = [
        (first + dt.timedelta(days=offset)).isoformat()
        for offset in range((last - first).days + 1)
        if (first + dt.timedelta(days=offset)) not in present
    ]
    split = DateSplit.chronological(archive)

    report: dict[str, object] = {
        "archive": {
            "root": str(Path(TLE_ROOT_DEFAULT).expanduser()),
            "date_first": first.isoformat(),
            "date_last": last.isoformat(),
            "file_count": len(archive.dates),
            "calendar_span_days": (last - first).days + 1,
            "missing_date_count": len(missing),
            "missing_dates": missing,
        },
        "split": split.as_dict()
        | {
            "train_files": len(split.available_dates(archive, "train")),
            "test_files": len(split.available_dates(archive, "test")),
        },
        "epochs": [],
    }

    for start in SAMPLE_STARTS:
        selection = select_elements(archive, start)
        satellites = SatelliteSet(selection.records)
        jd, fr = step_times(start, 1)
        healthy = satellites.healthy_indices(jd, fr)
        scan = scan_visibility(satellites.subset(healthy), jd, fr)

        altitude = scan.altitude_km[:, 0]
        entry: dict[str, object] = {
            "start_utc": start.isoformat(),
            "source_dates": [d.isoformat() for d in selection.source_dates],
            "selected": len(selection.records),
            "rejected_stale": selection.rejected_stale,
            "age_hours": selection.age_summary(),
            "healthy": int(healthy.size),
            "catalog_altitude_km": {
                "p05": _pct(altitude, 5),
                "p50": _pct(altitude, 50),
                "p95": _pct(altitude, 95),
            },
            "visible": {},
        }
        for mask_deg in ELEVATION_MASKS:
            visible = scan.visible(mask_deg)[:, 0]
            count = int(np.count_nonzero(visible))
            row: dict[str, float | int] = {"count": count}
            if count:
                row |= {
                    "alt_p05_km": _pct(altitude[visible], 5),
                    "alt_p50_km": _pct(altitude[visible], 50),
                    "alt_p95_km": _pct(altitude[visible], 95),
                    "slant_p50_km": _pct(scan.slant_range_km[visible, 0], 50),
                    "slant_max_km": float(scan.slant_range_km[visible, 0].max()),
                    "off_nadir_p50_deg": _pct(scan.off_nadir_deg[visible, 0], 50),
                    "off_nadir_max_deg": float(scan.off_nadir_deg[visible, 0].max()),
                    "horizon_off_nadir_at_p50_alt_deg": float(
                        horizon_off_nadir_deg(_pct(altitude[visible], 50))
                    ),
                }
            entry["visible"][f"elev_ge_{mask_deg:g}deg"] = row
        report["epochs"].append(entry)

    # Pass duration and angular rate, one long window, every elevation mask.
    start = SAMPLE_STARTS[-1]
    selection = select_elements(archive, start)
    satellites = SatelliteSet(selection.records)
    horizon_s = 3600.0
    coarse = 10.0
    steps = int(horizon_s / coarse) + 1
    jd, fr = step_times(start, steps, time_step_s=coarse)
    healthy = satellites.healthy_indices(jd, fr)
    scan = scan_visibility(satellites.subset(healthy), jd, fr)

    passes: dict[str, object] = {"window_s": horizon_s, "coarse_step_s": coarse}
    for mask_deg in (0.0,) + ELEVATION_MASKS:
        visible = scan.visible(mask_deg)
        durations: list[float] = []
        rates: list[float] = []
        for row_index in range(visible.shape[0]):
            row = visible[row_index]
            if not row.any() or row[0] or row[-1]:
                continue  # skip passes clipped by the window edges
            longest = current = 0
            for flag in row.tolist():
                current = current + 1 if flag else 0
                longest = max(longest, current)
            durations.append(longest * coarse)
            elevation = scan.elevation_deg[row_index][row]
            if elevation.size > 1:
                rates.append(float(np.abs(np.diff(elevation)).max() / coarse))
        passes[f"elev_ge_{mask_deg:g}deg"] = {
            "complete_passes": len(durations),
            "duration_p50_s": float(np.median(durations)) if durations else None,
            "duration_p95_s": (
                float(np.percentile(durations, 95)) if durations else None
            ),
            "duration_max_s": float(max(durations)) if durations else None,
            "elevation_rate_p95_deg_s": (
                float(np.percentile(rates, 95)) if rates else None
            ),
        }
    report["pass_statistics"] = passes

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
