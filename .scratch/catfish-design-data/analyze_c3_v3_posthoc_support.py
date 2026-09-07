#!/usr/bin/env python3
"""Descriptive C3 V3 premise screen over already-opened historical rows.

The inputs predate V3 and use a Q1-only, one-step, median-guard protocol.
This script only recomputes strict-load support and the agreement between the
canonical 112-D state's lagged-demand block and the later eligible-load sign.
It is not a V3 census, learner test, efficacy result, or seed authority.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
RESULT = HERE / "c3-disjoint-median-shadow-seeds-2026082801-2026082805-v1.json"
OBSERVATIONS = (
    HERE
    / "c3-disjoint-median-shadow-seeds-2026082801-2026082805-observations-v1.npz"
)
EXPECTED_RESULT_SHA256 = (
    "99915d786b5b00ad5e44dd4db6007113687588d99a9d82c0043c09de086938b3"
)
EXPECTED_OBSERVATIONS_SHA256 = (
    "970ee3ed5df2f7330c7fb7e8e46a0f15d54ec3fcaeb36aed9b220e01466461b0"
)
ACTION_DIM = 28
LOAD_BLOCK_OFFSET = 3 * ACTION_DIM


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def analyze() -> dict[str, Any]:
    if _sha256(RESULT) != EXPECTED_RESULT_SHA256:
        raise RuntimeError("historical C3 result hash drift")
    if _sha256(OBSERVATIONS) != EXPECTED_OBSERVATIONS_SHA256:
        raise RuntimeError("historical C3 observation hash drift")

    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    with np.load(OBSERVATIONS, allow_pickle=False) as archive:
        observations = np.asarray(archive["observation"], dtype=np.float64)
        keys = list(
            zip(
                archive["seed"].astype(int).tolist(),
                archive["step"].astype(int).tolist(),
                archive["user"].astype(int).tolist(),
                strict=True,
            )
        )
    if observations.shape != (5000, 4 * ACTION_DIM):
        raise RuntimeError("historical observation matrix shape drift")
    if len(set(keys)) != len(keys):
        raise RuntimeError("historical observation keys are not unique")
    row_index = {key: index for index, key in enumerate(keys)}
    users = int(payload["configuration"]["users"])

    candidate_rows = [
        row
        for rollout in payload["rollouts"]
        for row in rollout["candidate_rows"]
    ]
    load_rows = [
        row
        for row in candidate_rows
        if "source_load_reference" in row
        and "destination_load_reference" in row
    ]
    confusion: Counter[tuple[bool, bool]] = Counter()
    strict_power_by_anchor: dict[tuple[int, int, int], list[float]] = defaultdict(list)
    gap_pairs: list[tuple[float, float]] = []
    strict_rows = 0
    strict_old_guard_rows = 0

    for row in load_rows:
        key = (
            int(row["evaluation_seed"]),
            int(row["step_index"]),
            int(row["focal_user"]),
        )
        observation = observations[row_index[key]]
        source_action = int(row["reference_action"])
        destination_action = int(row["candidate_action"])
        if not (
            0 <= source_action < ACTION_DIM
            and 0 <= destination_action < ACTION_DIM
        ):
            raise RuntimeError("historical candidate action is outside the state block")

        previous_source = (
            observation[LOAD_BLOCK_OFFSET + source_action] * users
        )
        previous_destination = (
            observation[LOAD_BLOCK_OFFSET + destination_action] * users
        )
        current_source = int(row["source_load_reference"])
        current_destination = int(row["destination_load_reference"])
        actual_strict = current_source >= current_destination + 2
        lagged_strict = previous_source >= previous_destination + 2 - 1e-6
        confusion[(actual_strict, lagged_strict)] += 1
        gap_pairs.append(
            (
                float(previous_source - previous_destination),
                float(current_source - current_destination),
            )
        )
        if actual_strict:
            strict_rows += 1
            if row.get("power_certified") is True:
                strict_power_by_anchor[key].append(
                    float(previous_source - previous_destination)
                )
            if row.get("guard_retained") is True:
                strict_old_guard_rows += 1

    true_positive = confusion[(True, True)]
    false_positive = confusion[(False, True)]
    false_negative = confusion[(True, False)]
    true_negative = confusion[(False, False)]
    lagged_gap = np.asarray([row[0] for row in gap_pairs], dtype=np.float64)
    current_gap = np.asarray([row[1] for row in gap_pairs], dtype=np.float64)
    correlation = float(np.corrcoef(lagged_gap, current_gap)[0, 1])
    multi_choice = {
        key: values
        for key, values in strict_power_by_anchor.items()
        if len(values) >= 2
    }
    return {
        "schema": "c3-v3-posthoc-premise-screen-v1",
        "claim_type": "historical-descriptive-not-v3-evidence",
        "source_hashes": {
            RESULT.name: EXPECTED_RESULT_SHA256,
            OBSERVATIONS.name: EXPECTED_OBSERVATIONS_SHA256,
        },
        "denominators": {
            "historical_user_steps": int(observations.shape[0]),
            "historical_candidate_rows": len(candidate_rows),
            "load_bearing_candidate_rows": len(load_rows),
        },
        "strict_load_posthoc": {
            "rows": strict_rows,
            "anchors": len(strict_power_by_anchor),
            "anchors_with_at_least_two_choices": len(multi_choice),
            "anchors_with_at_least_two_choices_and_nonconstant_lagged_gap": sum(
                len({round(value, 6) for value in values}) >= 2
                for values in multi_choice.values()
            ),
            "rows_also_retained_by_historical_median_guard": strict_old_guard_rows,
        },
        "lagged_demand_vs_current_eligible_strict_gap": {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "true_negative": true_negative,
            "agreement": _ratio(true_positive + true_negative, len(load_rows)),
            "precision": _ratio(true_positive, true_positive + false_positive),
            "recall": _ratio(true_positive, true_positive + false_negative),
            "specificity": _ratio(true_negative, true_negative + false_positive),
            "gap_correlation": correlation,
            "gap_mean_absolute_error_users": float(
                np.mean(np.abs(lagged_gap - current_gap))
            ),
            "exact_gap_fraction": float(
                np.mean(np.isclose(lagged_gap, current_gap, atol=1e-5))
            ),
        },
        "claim_ceiling": (
            "The old rows make nonzero strict-load multi-choice support and "
            "a serious lagged-demand alias plausible. They cannot estimate "
            "V3 H3/release/power/surplus support, learnability, or EE effect."
        ),
    }


def main() -> int:
    print(json.dumps(analyze(), indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
