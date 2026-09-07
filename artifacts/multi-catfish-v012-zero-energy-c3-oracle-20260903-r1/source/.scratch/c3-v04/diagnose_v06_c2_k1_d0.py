#!/usr/bin/env python3
"""Post-outcome D0 diagnosis for the sealed V0.6 C2-k1 source.

This script never changes a policy, trains a model, or opens a new world.  It
only decomposes already-sealed T1 rows to test whether the network-total C2
label is dominated by non-focal continuation cascades, and re-scores the
already-selected oracle traces after removing offset 1 from the *evaluation*
window.  The latter is diagnostic only and is not a replacement gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Iterable


DEFAULT_SOURCE = Path(
    "artifacts/multi-catfish-v06-c2-k1-t1-source-gate-20260902-r1/"
    "merged/source.json"
)


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantiles(values: Iterable[float]) -> dict[str, float]:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot summarize an empty collection")

    def at(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        left = int(math.floor(position))
        right = int(math.ceil(position))
        if left == right:
            return ordered[left]
        weight = position - left
        return ordered[left] * (1.0 - weight) + ordered[right] * weight

    return {
        "min": ordered[0],
        "q25": at(0.25),
        "median": at(0.5),
        "q75": at(0.75),
        "max": ordered[-1],
        "mean": math.fsum(ordered) / len(ordered),
    }


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        stop = start + 1
        while stop < len(order) and values[order[stop]] == values[order[start]]:
            stop += 1
        average = 0.5 * ((start + 1) + stop)
        for position in range(start, stop):
            ranks[order[position]] = average
        start = stop
    return ranks


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        raise ValueError("correlation inputs disagree")
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_norm = math.sqrt(math.fsum(value * value for value in left_centered))
    right_norm = math.sqrt(math.fsum(value * value for value in right_centered))
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return math.fsum(
        first * second for first, second in zip(left_centered, right_centered, strict=True)
    ) / (left_norm * right_norm)


def _spearman(left: list[float], right: list[float]) -> float | None:
    return _pearson(_ranks(left), _ranks(right))


def _anchor_key(anchor: dict[str, Any]) -> str:
    return (
        f"{anchor['pool']}:{anchor['world_id']}:{anchor['step']}:"
        f"{anchor['focal_user']}"
    )


def _ratio(bits: float, energy: float) -> float:
    if energy <= 0.0:
        raise ValueError("energy must be positive")
    return bits / energy


def diagnose(source: dict[str, Any], *, source_file_sha256: str) -> dict[str, Any]:
    rows = source.get("rows")
    controls = source.get("controls")
    if not isinstance(rows, list) or not isinstance(controls, list):
        raise ValueError("sealed source lacks rows or controls")

    cascade_counts: list[int] = []
    changed_fractions: list[float] = []
    focal_rate_bits: list[float] = []
    nonfocal_rate_bits: list[float] = []
    energy_surplus_bits: list[float] = []
    bounded_nonfocal_abs_shares: list[float] = []
    nonfocal_to_target_abs: list[float] = []
    reconstruction_residuals: list[float] = []
    target_by_anchor: dict[str, dict[str, dict[int, float]]] = {}

    for row in rows:
        anchor = row["anchor"]
        focal = int(anchor["focal_user"])
        candidate_actions = row["candidate_k1_executed_actions"]
        reference_actions = row["reference_k1_executed_actions"]
        if len(candidate_actions) != 100 or len(reference_actions) != 100:
            raise ValueError("k1 action trace is not 100 users")
        changed = sum(
            candidate_actions[user] != reference_actions[user]
            for user in range(100)
            if user != focal
        )
        cascade_counts.append(changed)
        changed_fractions.append(changed / 99.0)

        dt = float(row["main_gauge_interval_s"])
        lam = float(row["main_gauge_lambda_bits_per_j"])
        candidate_rates = [float(value) for value in row["main_gauge_candidate_rates_k1"]]
        reference_rates = [float(value) for value in row["main_gauge_reference_rates_k1"]]
        if len(candidate_rates) != 100 or len(reference_rates) != 100:
            raise ValueError("k1 rate trace is not 100 users")
        focal_bits = dt * (candidate_rates[focal] - reference_rates[focal])
        nonfocal_bits = dt * math.fsum(
            candidate_rates[user] - reference_rates[user]
            for user in range(100)
            if user != focal
        )
        energy_bits = -lam * dt * (
            float(row["main_gauge_candidate_power_k1"])
            - float(row["main_gauge_reference_power_k1"])
        )
        target = float(row["z2_k1_bits"])
        residual = target - (focal_bits + nonfocal_bits + energy_bits)
        tolerance = 1e-9 * max(abs(target), 1.0)
        if abs(residual) > tolerance:
            raise ValueError("row target does not reconstruct from sealed k1 physics")
        denominator = abs(focal_bits) + abs(nonfocal_bits) + abs(energy_bits)
        bounded_share = abs(nonfocal_bits) / denominator if denominator > 0.0 else 0.0
        target_share = abs(nonfocal_bits) / abs(target) if target != 0.0 else 0.0
        focal_rate_bits.append(focal_bits)
        nonfocal_rate_bits.append(nonfocal_bits)
        energy_surplus_bits.append(energy_bits)
        bounded_nonfocal_abs_shares.append(bounded_share)
        nonfocal_to_target_abs.append(target_share)
        reconstruction_residuals.append(residual)

        key = _anchor_key(anchor)
        lineage = str(row["lineage"])
        action = int(row["opening_action"])
        target_by_anchor.setdefault(key, {}).setdefault(lineage, {})[action] = target

    pairwise_spearman: list[float] = []
    undefined_spearman = 0
    anchor_spearman: dict[str, dict[str, float | None]] = {}
    for key, lineages in sorted(target_by_anchor.items()):
        if set(lineages) != {"q13-a", "q13-b", "q13-c"}:
            raise ValueError("anchor lacks the frozen three lineages")
        anchor_spearman[key] = {}
        for left, right in (("q13-a", "q13-b"), ("q13-a", "q13-c"), ("q13-b", "q13-c")):
            actions = sorted(set(lineages[left]) & set(lineages[right]))
            if len(actions) != 28:
                raise ValueError("anchor/lineage pair lacks 28 actions")
            value = _spearman(
                [lineages[left][action] for action in actions],
                [lineages[right][action] for action in actions],
            )
            pair = f"{left}__{right}"
            anchor_spearman[key][pair] = value
            if value is None:
                undefined_spearman += 1
            else:
                pairwise_spearman.append(value)

    exclude = {1}
    indexed_controls: dict[tuple[int, str], dict[str, Any]] = {}
    for control in controls:
        identity = (int(control["anchor"]["world_id"]), str(control["lineage"]))
        if identity in indexed_controls:
            raise ValueError("control identity repeats")
        indexed_controls[identity] = control

    def totals(selected: Iterable[dict[str, Any]], arm: str) -> tuple[float, float]:
        bits = 0.0
        energy = 0.0
        field = f"{arm}_metrics"
        for control in selected:
            metrics = control[field]
            bits += math.fsum(
                float(value)
                for offset, value in enumerate(metrics["bits_by_offset"])
                if offset not in exclude
            )
            energy += math.fsum(
                float(value)
                for offset, value in enumerate(metrics["energy_by_offset"])
                if offset not in exclude
            )
        return bits, energy

    all_controls = list(indexed_controls.values())
    oracle_bits, oracle_energy = totals(all_controls, "oracle")
    drop_bits, drop_energy = totals(all_controls, "drop")
    lineage_positive: dict[str, bool] = {}
    for lineage in ("q13-a", "q13-b", "q13-c"):
        selected = [
            control for (_, row_lineage), control in indexed_controls.items()
            if row_lineage == lineage
        ]
        left = totals(selected, "oracle")
        right = totals(selected, "drop")
        lineage_positive[lineage] = _ratio(*left) > _ratio(*right)
    world_positive: dict[str, bool] = {}
    for world in sorted({identity[0] for identity in indexed_controls}):
        selected = [
            control for (row_world, _), control in indexed_controls.items()
            if row_world == world
        ]
        left = totals(selected, "oracle")
        right = totals(selected, "drop")
        world_positive[str(world)] = _ratio(*left) > _ratio(*right)

    report: dict[str, Any] = {
        "schema": "multi-catfish-mcrl-v06-c2-k1-d0-diagnostic-v1",
        "status": "POSTOUTCOME_DIAGNOSTIC_ONLY_NOT_A_GATE",
        "source": {
            "file_sha256": source_file_sha256,
            "embedded_source_sha256": source.get("source_sha256"),
            "rows": len(rows),
            "controls": len(controls),
            "test_split_opened": source.get("test_split_opened"),
        },
        "cascade": {
            "nonfocal_users_with_changed_k1_action": _quantiles(cascade_counts),
            "nonfocal_changed_fraction": _quantiles(changed_fractions),
            "rows_with_any_nonfocal_action_change": sum(value > 0 for value in cascade_counts),
            "rows_with_at_least_five_nonfocal_action_changes": sum(
                value >= 5 for value in cascade_counts
            ),
        },
        "target_decomposition": {
            "focal_rate_delta_bits": _quantiles(focal_rate_bits),
            "nonfocal_rate_delta_bits": _quantiles(nonfocal_rate_bits),
            "energy_surplus_delta_bits": _quantiles(energy_surplus_bits),
            "bounded_nonfocal_absolute_component_share": _quantiles(
                bounded_nonfocal_abs_shares
            ),
            "absolute_nonfocal_rate_over_absolute_target": _quantiles(
                nonfocal_to_target_abs
            ),
            "rows_bounded_nonfocal_share_ge_0_5": sum(
                value >= 0.5 for value in bounded_nonfocal_abs_shares
            ),
            "rows_bounded_nonfocal_share_ge_0_8": sum(
                value >= 0.8 for value in bounded_nonfocal_abs_shares
            ),
            "max_absolute_reconstruction_residual_bits": max(
                abs(value) for value in reconstruction_residuals
            ),
        },
        "cross_lineage_target_rank": {
            "defined_pairs": len(pairwise_spearman),
            "undefined_pairs": undefined_spearman,
            "spearman": _quantiles(pairwise_spearman),
            "by_anchor": anchor_spearman,
        },
        "oracle_rescore_excluding_offset_1": {
            "excluded_offsets": sorted(exclude),
            "oracle_ee_bits_per_j": _ratio(oracle_bits, oracle_energy),
            "drop_ee_bits_per_j": _ratio(drop_bits, drop_energy),
            "oracle_minus_drop_percent": 100.0
            * (_ratio(oracle_bits, oracle_energy) / _ratio(drop_bits, drop_energy) - 1.0),
            "pooled_positive": _ratio(oracle_bits, oracle_energy)
            > _ratio(drop_bits, drop_energy),
            "positive_lineages": sum(lineage_positive.values()),
            "lineage_positive": lineage_positive,
            "positive_worlds": sum(world_positive.values()),
            "world_positive": world_positive,
        },
        "interpretation_boundary": {
            "training": False,
            "policy_selection": False,
            "new_worlds": False,
            "replacement_gate": False,
        },
    }
    report["diagnostic_sha256"] = _canonical_sha256(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    report = diagnose(source, source_file_sha256=_file_sha256(args.source))
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
