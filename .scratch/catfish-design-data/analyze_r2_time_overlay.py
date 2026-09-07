#!/usr/bin/env python3
"""Apply conditional time-only R2 overlays to a read-only legacy receipt.

The script deliberately excludes phi2 rows without a visible incumbent because
the current receipt cannot distinguish a sourced served-to-served handover from
re-entry by the reward label alone. It never supplies an E_HO value.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


EXPECTED_INPUT_SHA256 = (
    "8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2"
)
DECISION_INTERVAL_S = 30.08
INTERRUPTION_S = {"none": 0.0, "phi1": 0.062, "phi2": 0.142}
FULL_DELAY_S = {"none": 0.0, "phi1": 0.072, "phi2": 0.152}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyse(path: Path) -> dict[str, Any]:
    observed_hash = _sha256(path)
    if observed_hash != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"input SHA-256 mismatch: {observed_hash} != {EXPECTED_INPUT_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    total_rows = 0
    counts: collections.Counter[str] = collections.Counter()
    interruption_rewards: list[float] = []
    full_delay_rewards: list[float] = []
    reference_r1: list[float] = []
    for rollout in payload["rollouts"]:
        for row in rollout["proposal_rows"]:
            total_rows += 1
            metrics = row["reference"]
            event = str(metrics["focal_handover"])
            if event not in INTERRUPTION_S:
                raise ValueError(f"unexpected handover class {event!r}")
            if event == "phi2" and row["visible_incumbent_key"] is None:
                counts["phi2_reentry_excluded"] += 1
                continue
            rate_bps = float(metrics["focal_rate_bps"])
            power_w = float(metrics["system_power_w"])
            if rate_bps < 0.0 or power_w <= 0.0:
                raise ValueError("reference rate/power violates reward domain")
            counts[event] += 1
            reference_r1.append(rate_bps / power_w)
            interruption_rewards.append(
                -rate_bps * INTERRUPTION_S[event] / (power_w * DECISION_INTERVAL_S)
            )
            full_delay_rewards.append(
                -rate_bps * FULL_DELAY_S[event] / (power_w * DECISION_INTERVAL_S)
            )
    included = len(interruption_rewards)
    nonzero = [abs(value) for value in interruption_rewards if value]
    mean_abs = statistics.fmean(abs(value) for value in interruption_rewards)
    mean_r1 = statistics.fmean(reference_r1)
    return {
        "schema": "catfish-r2-time-overlay-v1",
        "input_sha256": observed_hash,
        "geometry": "legacy-narrow sensitivity only",
        "decision_interval_s": DECISION_INTERVAL_S,
        "conditional_time_proxies_s": {
            "interruption": INTERRUPTION_S,
            "full_delay": FULL_DELAY_S,
        },
        "sampled_user_decisions": total_rows,
        "conditionally_scored_rows": included,
        "event_counts": dict(sorted(counts.items())),
        "mean_r2_interruption_bits_per_j_over_scored_rows": statistics.fmean(
            interruption_rewards
        ),
        "mean_r2_full_delay_bits_per_j_over_scored_rows": statistics.fmean(
            full_delay_rewards
        ),
        "mean_abs_r2_interruption_bits_per_j_over_scored_rows": mean_abs,
        "mean_abs_nonzero_r2_interruption_bits_per_j": statistics.fmean(nonzero),
        "mean_reference_r1_bits_per_j_over_scored_rows": mean_r1,
        "ratio_mean_abs_r2_to_mean_r1": mean_abs / mean_r1,
        "known_numerator_divided_by_all_sampled_rows_bits_per_j": sum(
            interruption_rewards
        )
        / total_rows,
        "claim_ceiling": (
            "conditional E_HO=0 timing overlay on sampled legacy-narrow rows; "
            "62/142 and 72/152 ms mappings are not accepted primary values; "
            "re-entry is unscored; no causal, learning, primary-geometry, or "
            "Catfish-effectiveness claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyse(args.input), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
