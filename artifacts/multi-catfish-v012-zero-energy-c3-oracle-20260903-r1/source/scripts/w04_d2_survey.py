"""Measure D2 behaviour at the frozen thresholds and across the sweep axis.

Pre-probe data-property survey, not probe P1: P1 answers pre-registered
questions against a frozen threshold set (§7.1), and cannot be run before
W-13 freezes them.  What this gives is the order of magnitude W-04 needs to
be checkable at all — event rates, eligible-set sizes, and how often a user
has no eligible satellite (the §4A.5a(4) outage input).

    .venv/bin/python scripts/w04_d2_survey.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcrl.env.action_contract import NUM_SATELLITE_SLOTS  # noqa: E402
from mcrl.env.constants import R_E_KM, TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.d2 import (  # noqa: E402
    THRESH2_SWEEP_KM,
    D2Config,
    D2Tracker,
    elevation_for_slant_range,
)
from mcrl.env.ephemeris import (  # noqa: E402
    SatelliteSet,
    select_elements,
    service_area_center_ecef,
    step_times,
)
from mcrl.env.geometry import range_rate_km_s  # noqa: E402
from mcrl.env.tle import TleArchive  # noqa: E402

STARTS = [
    dt.datetime(2025, 8, 15, 3, 0, tzinfo=dt.timezone.utc),
    dt.datetime(2025, 12, 3, 11, 30, tzinfo=dt.timezone.utc),
    dt.datetime(2026, 4, 9, 18, 45, tzinfo=dt.timezone.utc),
    dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc),
]
HORIZON_STEPS = 600
MEASURED_ALTITUDE_KM = 485.0


def _geometry(archive, start, warmup, steps):
    origin = start - dt.timedelta(seconds=warmup)
    jd, fr = step_times(origin, steps + warmup)
    satellites = SatelliteSet(select_elements(archive, start).records)
    subset = satellites.subset(satellites.healthy_indices(jd, fr))
    ground = service_area_center_ecef()
    position, velocity = subset.propagate_ecef_state(jd, fr)
    return (
        subset.norad_ids,
        np.linalg.norm(position - ground, axis=-1),
        np.linalg.norm(position, axis=-1) - R_E_KM,
        range_rate_km_s(position, velocity, ground),
    )


def _run(norad_ids, slant, altitude, rate, config, steps, warmup):
    tracker = D2Tracker(norad_ids, 1, config)
    tracker.prime(
        slant_range_km=slant[None, :, :warmup],
        altitude_km=altitude[:, :warmup],
        range_rate_km_s=rate[None, :, :warmup],
    )
    eligible_counts: list[int] = []
    entries = 0
    exits = 0
    starved = 0
    previous = tracker.latched[0]
    for step in range(steps):
        column = warmup + step
        snapshot = tracker.update(
            step,
            slant_range_km=slant[None, :, column],
            altitude_km=altitude[:, column],
            range_rate_km_s=rate[None, :, column],
        )
        current = snapshot.eligible[0]
        entries += int(np.count_nonzero(current & ~previous))
        exits += int(np.count_nonzero(~current & previous))
        previous = current
        count = int(current.sum())
        eligible_counts.append(count)
        if count == 0:
            starved += 1
    counts = np.array(eligible_counts, dtype=np.float64)
    return {
        "eligible_p05": float(np.percentile(counts, 5)),
        "eligible_p50": float(np.percentile(counts, 50)),
        "eligible_p95": float(np.percentile(counts, 95)),
        "eligible_min": float(counts.min()),
        "entries_per_1000_steps": 1000.0 * entries / steps,
        "exits_per_1000_steps": 1000.0 * exits / steps,
        "steps_with_no_candidate": starved,
        "starvation_rate": starved / steps,
        "slots_always_fillable": bool(counts.min() >= NUM_SATELLITE_SLOTS),
    }


def main() -> None:
    archive = TleArchive(TLE_ROOT_DEFAULT)
    base = D2Config()
    warmup = base.warmup_steps

    report: dict[str, object] = {
        "config": base.as_dict(),
        "elevation_disclosure": {
            f"{altitude:g}km": {
                key: (round(value, 2) if isinstance(value, float) else value)
                for key, value in base.elevation_disclosure(altitude).items()
            }
            for altitude in (780.0, 550.0, MEASURED_ALTITUDE_KM, 426.0)
        },
        "sweep_axis_elevation_at_measured_altitude": {
            f"{threshold:g}km": round(
                elevation_for_slant_range(threshold, MEASURED_ALTITUDE_KM), 2
            )
            for threshold in THRESH2_SWEEP_KM
        },
        "epochs": [],
        "thresh2_sweep": {},
    }

    cache = {}
    for start in STARTS:
        geometry = _geometry(archive, start, warmup, HORIZON_STEPS)
        cache[start] = geometry
        report["epochs"].append(
            {"start_utc": start.isoformat(), "satellites_tracked": len(geometry[0])}
            | _run(*geometry, base, HORIZON_STEPS, warmup)
        )

    reference = cache[STARTS[-1]]
    for threshold in THRESH2_SWEEP_KM:
        config = D2Config(thresh2_km=threshold)
        report["thresh2_sweep"][f"{threshold:g}km"] = {
            "elevation_deg": round(
                elevation_for_slant_range(threshold, MEASURED_ALTITUDE_KM), 2
            )
        } | _run(*reference, config, HORIZON_STEPS, config.warmup_steps)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
