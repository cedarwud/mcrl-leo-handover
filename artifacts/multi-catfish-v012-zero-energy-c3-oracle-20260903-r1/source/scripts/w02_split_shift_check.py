"""Does the split scheme put a distribution shift on the train/test axis?

W-02 measured two trends across the corpus — the constellation grows and
the visible-satellite altitude drifts down — and a single chronological cut
puts both of them straight onto the train/test axis.  The author's ruling
replaces that with block-alternating blocks plus an embargo.

This script measures both schemes on the same quantities so the claim
"alternating removes the shift" is checked rather than asserted.

    .venv/bin/python scripts/w02_split_shift_check.py
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcrl.env.constants import TLE_ROOT_DEFAULT  # noqa: E402
from mcrl.env.ephemeris import (  # noqa: E402
    TEST,
    TRAIN,
    BlockAlternatingSplit,
    ContiguousDateSplit,
    SatelliteSet,
    scan_visibility,
    select_elements,
    step_times,
)
from mcrl.env.tle import TleArchive  # noqa: E402

DATES_PER_PART = 60
MIN_ELEVATION_DEG = 10.0


def _probe(archive: TleArchive, dates, rng) -> dict[str, float]:
    """Constellation size and visible-satellite altitude over sampled dates."""
    picked = sorted(
        rng.choice(len(dates), size=min(DATES_PER_PART, len(dates)), replace=False)
    )
    selected_counts: list[int] = []
    visible_counts: list[int] = []
    altitudes: list[float] = []
    for index in picked:
        start = dt.datetime.combine(
            dates[int(index)], dt.time(6, 0), tzinfo=dt.timezone.utc
        )
        selection = select_elements(archive, start)
        satellites = SatelliteSet(selection.records)
        jd, fr = step_times(start, 1)
        healthy = satellites.healthy_indices(jd, fr)
        scan = scan_visibility(satellites.subset(healthy), jd, fr)
        visible = scan.visible(MIN_ELEVATION_DEG)[:, 0]
        selected_counts.append(len(selection.records))
        visible_counts.append(int(np.count_nonzero(visible)))
        if visible.any():
            altitudes.append(float(np.median(scan.altitude_km[visible, 0])))
    return {
        "dates_probed": float(len(picked)),
        "selected_mean": float(np.mean(selected_counts)),
        "visible_mean": float(np.mean(visible_counts)),
        "visible_altitude_p50_mean_km": float(np.mean(altitudes)),
    }


def main() -> None:
    archive = TleArchive(TLE_ROOT_DEFAULT)
    report: dict[str, object] = {}

    schemes = {
        "contiguous_chronological_SUPERSEDED": ContiguousDateSplit.chronological(
            archive
        ),
        "block_alternating_7d_embargo_1d": BlockAlternatingSplit.for_archive(
            archive
        ),
    }
    for name, split in schemes.items():
        rng = np.random.default_rng(20260822)
        entry: dict[str, object] = {"config": split.as_dict()}
        for part in (TRAIN, TEST):
            dates = split.available_dates(archive, part)
            entry[part] = {"file_count": len(dates)} | _probe(archive, dates, rng)
        train, test = entry[TRAIN], entry[TEST]
        entry["shift"] = {
            "selected_ratio_test_over_train": test["selected_mean"]
            / train["selected_mean"],
            "visible_ratio_test_over_train": test["visible_mean"]
            / train["visible_mean"],
            "altitude_delta_km_test_minus_train": (
                test["visible_altitude_p50_mean_km"]
                - train["visible_altitude_p50_mean_km"]
            ),
        }
        if isinstance(split, BlockAlternatingSplit):
            entry["embargoed_files"] = len(split.embargoed_dates(archive))
            entry["minimum_train_test_gap_days"] = split.minimum_gap_days(archive)
        report[name] = entry

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
