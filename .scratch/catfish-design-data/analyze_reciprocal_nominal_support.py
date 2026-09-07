#!/usr/bin/env python3
"""Count nominal reciprocal-pair support in an existing read-only receipt.

This script does not evaluate a new action or infer execution-time feasibility.
It uses only the sampled users' stored physical candidate keys, reference keys,
visible incumbents, and reference handover classes.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


EXPECTED_INPUT_SHA256 = (
    "8efb3068537a10dd8896d07d5410986976b40a6181532ded876648c4474e01a2"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _key(value: Any) -> tuple[int, int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"invalid physical key: {value!r}")
    return int(value[0]), int(value[1])


def _handover_class(
    incumbent: tuple[int, int] | None, candidate: tuple[int, int]
) -> str | None:
    if incumbent is None:
        return None
    if incumbent == candidate:
        return "none"
    return "phi1" if incumbent[0] == candidate[0] else "phi2"


def _candidate_keys(row: dict[str, Any]) -> set[tuple[int, int]]:
    keys = [_key(item["key"]) for item in row["selection_candidates"]]
    if any(key is None for key in keys):
        raise ValueError("a valid selection candidate has no physical key")
    concrete = {key for key in keys if key is not None}
    if len(concrete) != len(keys):
        raise ValueError("selection candidates contain duplicate physical keys")
    return concrete


def reciprocal_pair_is_nominally_eligible(
    left: dict[str, Any], right: dict[str, Any]
) -> bool:
    left_reference = _key(left["reference_key"])
    right_reference = _key(right["reference_key"])
    if (
        left_reference is None
        or right_reference is None
        or left_reference == right_reference
        or not bool(left["reference"]["focal_served"])
        or not bool(right["reference"]["focal_served"])
    ):
        return False
    if (
        right_reference not in _candidate_keys(left)
        or left_reference not in _candidate_keys(right)
    ):
        return False
    left_class = _handover_class(
        _key(left["visible_incumbent_key"]), right_reference
    )
    right_class = _handover_class(
        _key(right["visible_incumbent_key"]), left_reference
    )
    return (
        left_class == left["reference"]["focal_handover"]
        and right_class == right["reference"]["focal_handover"]
    )


def analyse(path: Path) -> dict[str, Any]:
    observed_hash = _sha256(path)
    if observed_hash != EXPECTED_INPUT_SHA256:
        raise ValueError(
            f"input SHA-256 mismatch: {observed_hash} != {EXPECTED_INPUT_SHA256}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    per_step: list[int] = []
    sampled_users: set[int] = set()
    for rollout in payload["rollouts"]:
        by_step: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
        for row in rollout["proposal_rows"]:
            by_step[int(row["step_index"])].append(row)
        for rows in by_step.values():
            sampled_users.add(len(rows))
            count = sum(
                reciprocal_pair_is_nominally_eligible(left, right)
                for left, right in itertools.combinations(rows, 2)
            )
            per_step.append(int(count))
    histogram = collections.Counter(per_step)
    total = int(sum(per_step))
    steps_with_pair = int(sum(count > 0 for count in per_step))
    return {
        "schema": "catfish-reciprocal-nominal-support-v1",
        "input_sha256": observed_hash,
        "geometry": "legacy-narrow sensitivity only",
        "sampled_steps": len(per_step),
        "sampled_users_per_step_values": sorted(sampled_users),
        "nominal_reciprocal_pairs": total,
        "steps_with_at_least_one_pair": steps_with_pair,
        "fraction_steps_with_at_least_one_pair": steps_with_pair / len(per_step),
        "mean_pairs_per_sampled_step": total / len(per_step),
        "maximum_pairs_in_one_sampled_step": max(per_step),
        "pair_count_histogram": {
            str(key): int(histogram[key]) for key in sorted(histogram)
        },
        "claim_ceiling": (
            "sampled-subset nominal candidate support only; no swapped-action "
            "evaluation, execution feasibility, realised invariant, power, EE, "
            "primary-geometry, learning, or Catfish effectiveness claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyse(args.input), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
