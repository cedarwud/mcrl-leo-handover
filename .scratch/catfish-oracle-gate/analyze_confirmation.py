#!/usr/bin/env python3
"""Post-result descriptive audit of the frozen Catfish oracle receipt.

This script does not alter the frozen gate or make a new pass/fail decision.
It exposes clustering, active-set transitions, and effect distributions needed
to interpret the precommitted result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "confirmation-seeds-10-k10-v1.json"
DEFAULT_OUTPUT = HERE / "confirmation-derived-analysis-v1.json"
T_CRITICAL_DF9_95 = 2.2621571628540993


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _mean(values: Iterable[float]) -> float:
    rows = list(values)
    return float(statistics.fmean(rows)) if rows else 0.0


def _quantile(values: Sequence[float], probability: float) -> float:
    rows = sorted(float(value) for value in values)
    if not rows:
        return 0.0
    position = probability * (len(rows) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return rows[lower]
    weight = position - lower
    return float(rows[lower] * (1.0 - weight) + rows[upper] * weight)


def _distribution(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": _mean(values),
        "p05": _quantile(values, 0.05),
        "p25": _quantile(values, 0.25),
        "median": _quantile(values, 0.50),
        "p75": _quantile(values, 0.75),
        "p95": _quantile(values, 0.95),
        "min": float(min(values)) if values else 0.0,
        "max": float(max(values)) if values else 0.0,
    }


def _seed_rate_ci(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rates = []
    by_seed: dict[str, float] = {}
    for seed in sorted({int(row["evaluation_seed"]) for row in rows}):
        seed_rows = [row for row in rows if int(row["evaluation_seed"]) == seed]
        rate = _mean(float(bool(row["jointly_positive"])) for row in seed_rows)
        rates.append(rate)
        by_seed[str(seed)] = rate
    mean = _mean(rates)
    standard_error = (
        float(statistics.stdev(rates) / math.sqrt(len(rates)))
        if len(rates) > 1
        else 0.0
    )
    half_width = T_CRITICAL_DF9_95 * standard_error if len(rates) == 10 else 0.0
    return {
        "by_seed": by_seed,
        "mean": mean,
        "standard_error": standard_error,
        "paired_seed_t95_ci": [mean - half_width, mean + half_width],
        "note": "descriptive CI; the frozen gate uses the point threshold, not this CI",
    }


def _delta_label(row: dict[str, Any], *, realised: bool) -> str:
    if realised:
        added = len(row["realised_active_beams_added"])
        removed = len(row["realised_active_beams_removed"])
    else:
        added = len(row["intended_beams_added"])
        removed = len(row["intended_beams_removed"])
    return f"add{added}_remove{removed}_net{added - removed:+d}"


def _transition_counts(
    rows: Sequence[dict[str, Any]], *, realised: bool
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(_delta_label(row, realised=realised), []).append(row)
    return {
        label: {
            "rows": len(group),
            "role_positive": sum(bool(row["role_positive"]) for row in group),
            "ee_positive": sum(bool(row["ee_positive"]) for row in group),
            "jointly_positive": sum(
                bool(row["jointly_positive"]) for row in group
            ),
            "jointly_positive_fraction": _mean(
                float(bool(row["jointly_positive"])) for row in group
            ),
            "mean_delta_ee_mbit_per_j": _mean(
                float(row["delta_ee_bits_per_j"]) / 1e6 for row in group
            ),
        }
        for label, group in sorted(groups.items())
    }


def _family(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    joint = [row for row in rows if row["jointly_positive"]]
    role = [row for row in rows if row["role_positive"]]
    service_unsafe = [row for row in rows if not row["service_safe"]]
    cross = Counter(
        (
            bool(row["role_positive"]),
            bool(row["ee_positive"]),
            bool(row["service_safe"]),
        )
        for row in rows
    )
    result: dict[str, Any] = {
        "eligible": len(rows),
        "role_positive": len(role),
        "ee_positive": sum(bool(row["ee_positive"]) for row in rows),
        "service_unsafe": len(service_unsafe),
        "jointly_positive": len(joint),
        "jointly_positive_fraction": _mean(
            float(bool(row["jointly_positive"])) for row in rows
        ),
        "seed_clustered_joint_rate": _seed_rate_ci(rows),
        "role_ee_service_crosstab": {
            f"role={role_value},ee={ee_value},safe={safe_value}": count
            for (role_value, ee_value, safe_value), count in sorted(cross.items())
        },
        "all_delta_ee_mbit_per_j": _distribution(
            [float(row["delta_ee_bits_per_j"]) / 1e6 for row in rows]
        ),
        "role_positive_delta_ee_mbit_per_j": _distribution(
            [float(row["delta_ee_bits_per_j"]) / 1e6 for row in role]
        ),
        "joint_delta_ee_mbit_per_j": _distribution(
            [float(row["delta_ee_bits_per_j"]) / 1e6 for row in joint]
        ),
        "all_delta_effective_beams": _distribution(
            [
                float(row["alternative_effective_beams"])
                - float(row["reference_effective_beams"])
                for row in rows
            ]
        ),
        "joint_delta_effective_beams": _distribution(
            [
                float(row["alternative_effective_beams"])
                - float(row["reference_effective_beams"])
                for row in joint
            ]
        ),
        "all_delta_load_relief": _distribution(
            [float(row["delta_load_relief"]) for row in rows]
        ),
        "joint_delta_load_relief": _distribution(
            [float(row["delta_load_relief"]) for row in joint]
        ),
        "intended_set_transitions": _transition_counts(rows, realised=False),
        "realised_set_transitions": _transition_counts(rows, realised=True),
        "max_abs_identity_residual_bits_per_j": max(
            abs(float(row["identity_residual_bits_per_j"])) for row in rows
        ),
    }
    if rows[0]["family"].startswith("r2_"):
        result["required_avoided_handover_equivalent_mbps"] = _distribution(
            [
                float(row["required_avoided_handover_equivalent_bps"]) / 1e6
                for row in rows
            ]
        )
        result["required_avoided_handover_power_w"] = _distribution(
            [float(row["required_avoided_handover_power_w"]) for row in rows]
        )
    else:
        result["realised_proposed_beam_opening"] = sum(
            bool(row["realised_proposed_beam_opening"]) for row in rows
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    receipt = json.loads(args.input.read_text(encoding="utf-8"))
    if receipt["status"] != "complete" or receipt["stage"] != "confirmation":
        raise RuntimeError("input is not a completed confirmation receipt")
    rows = [
        row
        for rollout in receipt["rollouts"]
        for row in rollout["proposal_rows"]
        if row["status"] == "evaluated"
    ]
    baseline = [
        step["metrics"]
        for rollout in receipt["rollouts"]
        for step in rollout["baseline_steps"]
    ]
    families = sorted({str(row["family"]) for row in rows})
    output = {
        "schema": "mcrl-catfish-oracle-post-result-description-v1",
        "status": "complete",
        "claim_boundary": (
            "post-result descriptive audit only; frozen proposal generation, "
            "thresholds, and gate decisions are unchanged"
        ),
        "input_path": str(args.input),
        "input_sha256": _sha256(args.input),
        "independent_unit": "evaluation seed",
        "baseline_projection": {
            "steps": len(baseline),
            "mean_ee_mbit_per_j": _mean(
                float(row["system_ee_bits_per_j"]) / 1e6 for row in baseline
            ),
            "mean_throughput_gbps": _mean(
                float(row["system_throughput_bps"]) / 1e9 for row in baseline
            ),
            "mean_power_w": _mean(float(row["system_power_w"]) for row in baseline),
            "mean_served": _mean(float(row["served"]) for row in baseline),
            "mean_effective_beams": _mean(float(row["eff_beams"]) for row in baseline),
        },
        "families": {
            family: _family([row for row in rows if row["family"] == family])
            for family in families
        },
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
