#!/usr/bin/env python3
"""Derive compact, reproducible diagnostics from the verified v2 receipt."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot take a quantile of no values")
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _stats(values: Sequence[float]) -> dict[str, float | int] | None:
    finite = [float(value) for value in values if math.isfinite(float(value))]
    if not finite:
        return None
    return {
        "n": len(finite),
        "mean": statistics.fmean(finite),
        "median": statistics.median(finite),
        "p05": _quantile(finite, 0.05),
        "p95": _quantile(finite, 0.95),
        "min": min(finite),
        "max": max(finite),
    }


def _metric_bundle(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rows": len(rows),
        "delta_ee_mbit_per_j": _stats(
            [float(row["delta_ee_bits_per_j"]) / 1e6 for row in rows]
        ),
        "delta_throughput_gbit_per_s": _stats(
            [float(row["delta_throughput_bps"]) / 1e9 for row in rows]
        ),
        "delta_power_w": _stats([float(row["delta_power_w"]) for row in rows]),
        "focal_rate_delta_gbit_per_s": _stats(
            [float(row["focal_rate_delta_bps"]) / 1e9 for row in rows]
        ),
        "other_users_rate_delta_gbit_per_s": _stats(
            [float(row["other_users_rate_delta_bps"]) / 1e9 for row in rows]
        ),
    }


def _seed_rate_interval(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    seeds = sorted({int(row["evaluation_seed"]) for row in rows})
    rates = []
    for seed in seeds:
        seed_rows = [row for row in rows if int(row["evaluation_seed"]) == seed]
        rates.append(
            sum(bool(row["jointly_positive"]) for row in seed_rows) / len(seed_rows)
        )
    mean = statistics.fmean(rates)
    standard_error = statistics.stdev(rates) / math.sqrt(len(rates))
    t_975_df9 = 2.2621571628540993
    return {
        "independent_unit": "evaluation_seed",
        "seed_rates": rates,
        "mean": mean,
        "descriptive_t95_low": mean - t_975_df9 * standard_error,
        "descriptive_t95_high": mean + t_975_df9 * standard_error,
    }


def _topology_counts(rows: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        label = (
            f"added={len(row['realised_active_beams_added'])},"
            f"removed={len(row['realised_active_beams_removed'])},"
            f"effective_delta="
            f"{int(row['alternative_effective_beams']) - int(row['reference_effective_beams'])},"
            f"proposed_opening={bool(row['realised_proposed_beam_opening'])}"
        )
        counts[label] += 1
    return dict(sorted(counts.items()))


def _candidate_for_key(
    row: dict[str, Any], key_name: str
) -> dict[str, Any] | None:
    key = row[key_name]
    if key is None:
        return None
    for candidate in row["selection_candidates"]:
        if candidate["key"] == key:
            return candidate
    return None


def _observable_features(row: dict[str, Any]) -> dict[str, float]:
    reference = _candidate_for_key(row, "reference_key")
    alternatives = [
        candidate
        for candidate in row["selection_candidates"]
        if candidate["key"] != row["reference_key"]
    ]
    output = {
        "proposal_candidate_sinr": float(row["proposal_candidate_sinr"]),
        "valid_physical_candidate_count": float(len(row["selection_candidates"])),
        "previous_inactive_alternative_count": float(
            sum(float(candidate["prior_demand"]) == 0.0 for candidate in alternatives)
        ),
        "visible_incumbent": float(row["visible_incumbent_action"] is not None),
    }
    if row["reference_prior_demand"] is not None:
        output["reference_prior_demand"] = float(row["reference_prior_demand"])
    if reference is not None:
        reference_sinr = float(reference["candidate_sinr"])
        output["reference_candidate_sinr"] = reference_sinr
        output["proposal_minus_reference_sinr"] = (
            float(row["proposal_candidate_sinr"]) - reference_sinr
        )
    return output


def _feature_comparison(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    groups = {
        "jointly_positive": [row for row in rows if row["jointly_positive"]],
        "not_jointly_positive": [
            row for row in rows if not row["jointly_positive"]
        ],
        "role_positive": [row for row in rows if row["role_positive"]],
        "ee_positive": [row for row in rows if row["ee_positive"]],
    }
    output: dict[str, Any] = {}
    for group, group_rows in groups.items():
        features = [_observable_features(row) for row in group_rows]
        names = sorted({name for feature in features for name in feature})
        output[group] = {
            "rows": len(group_rows),
            "features": {
                name: _stats(
                    [feature[name] for feature in features if name in feature]
                )
                for name in names
            },
        }
    return output


def _family_analysis(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    subsets: dict[str, Callable[[dict[str, Any]], bool]] = {
        "all_evaluated": lambda row: True,
        "role_positive": lambda row: bool(row["role_positive"]),
        "ee_positive": lambda row: bool(row["ee_positive"]),
        "jointly_positive": lambda row: bool(row["jointly_positive"]),
        "service_unsafe": lambda row: not bool(row["service_safe"]),
    }
    return {
        "subsets": {
            name: _metric_bundle([row for row in rows if predicate(row)])
            for name, predicate in subsets.items()
        },
        "seed_clustered_joint_rate": _seed_rate_interval(rows),
        "topology_counts": _topology_counts(rows),
    }


def main() -> int:
    args = _arguments()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    payload = json.loads(args.receipt.read_text(encoding="utf-8"))
    if payload.get("status") != "complete" or payload.get("stage") != "confirmation":
        raise RuntimeError("input is not a complete confirmation receipt")
    rows = [
        row
        for rollout in payload["rollouts"]
        for row in rollout["proposal_rows"]
        if row["status"] == "evaluated"
    ]
    by_family = {
        family: [row for row in rows if row["family"] == family]
        for family in payload["family_summary"]
    }
    result: dict[str, Any] = {
        "schema": "mcrl-catfish-state-observable-derived-v2",
        "source_receipt": str(args.receipt),
        "source_receipt_sha256": __import__("hashlib").sha256(
            args.receipt.read_bytes()
        ).hexdigest(),
        "family_summary": payload["family_summary"],
        "family_analysis": {
            family: _family_analysis(family_rows)
            for family, family_rows in by_family.items()
        },
        "r3_prev_inactive_split_observable_feature_comparison": (
            _feature_comparison(by_family["r3_prev_inactive_split"])
        ),
        "r2_break_even": {
            "required_avoided_handover_equivalent_mbit_per_s": _stats(
                [
                    float(row["required_avoided_handover_equivalent_bps"]) / 1e6
                    for row in by_family["r2_access_exact_stay"]
                ]
            ),
            "required_avoided_handover_power_w": _stats(
                [
                    float(row["required_avoided_handover_power_w"])
                    for row in by_family["r2_access_exact_stay"]
                ]
            ),
        },
        "claim_boundary": (
            "descriptive one-focal counterfactual diagnostics only; no selection "
            "model, joint composition, long-horizon, or trained-policy claim"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
