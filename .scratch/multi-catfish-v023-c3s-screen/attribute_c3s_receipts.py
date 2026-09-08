#!/usr/bin/env python3
"""Offline attribution for immutable v1 C3-S unit receipts."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "multi-catfish-mcrl-v023-c3s-v1-offline-attribution-v1"  # Task-specific output schema.
ARMS = ("BASE", "FULL", "LITE")  # Sealed v1 receipt arm set.
COORDINATOR_ARMS = ("FULL", "LITE")  # Sealed v1 coordinator arms.
DEFAULT_RECEIPTS = Path(  # User-supplied read-only v1 receipt root.
    "/home/sat/mcrl-v023-c3s-run/.scratch/multi-catfish-v023-c3s-screen/"
    "runs/c3s-20260908-r1"
)


class AttributionError(RuntimeError):
    """The v1 receipt panel is incomplete or malformed."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="ascii"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AttributionError(f"cannot read receipt: {path}") from error
    if not isinstance(value, dict):
        raise AttributionError(f"receipt is not an object: {path}")
    return value


def _hex(value: object) -> Fraction:
    try:
        parsed = float.fromhex(str(value))
    except (ValueError, OverflowError) as error:
        raise AttributionError("receipt metric is not float hex") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise AttributionError("receipt metric is non-finite or negative")
    return Fraction.from_float(parsed)


def _fraction(value: Mapping[str, object]) -> Fraction:
    try:
        return Fraction(int(value["numerator"]), int(value["denominator"]))
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        raise AttributionError("exact fraction payload is malformed") from error


def _fp(value: Fraction) -> dict[str, object]:
    return {
        "numerator": str(value.numerator), "denominator": str(value.denominator),
        "float": float(value), "float_hex": float(value).hex(),
    }


def _kind(profile_id: str) -> str:
    if profile_id == "BASE":
        return "BASE"
    if profile_id.startswith("U:"):
        return "unilateral"
    if profile_id.startswith("J:"):
        return "evacuation"
    raise AttributionError(f"unknown selected profile ID: {profile_id}")


def _decision_rows(receipt: Mapping[str, object], arm: str) -> list[Mapping[str, object]]:
    rows = receipt.get("decisions_by_arm")
    if not isinstance(rows, Mapping) or not isinstance(rows.get(arm), list):
        raise AttributionError(f"receipt lacks {arm} decision rows")
    if not all(isinstance(row, Mapping) for row in rows[arm]):
        raise AttributionError(f"receipt has malformed {arm} decision rows")
    return rows[arm]  # type: ignore[return-value]


def attribute(root: Path) -> dict[str, object]:
    """Attribute catalog choices and temporal realised gains without simulation."""

    paths = sorted(Path(root).glob("units/*/receipt.json"))
    if len(paths) != 12:
        raise AttributionError(f"expected 12 unit receipts, found {len(paths)}")
    receipts = [_load(path) for path in paths]
    terminal_path = Path(root) / "terminal" / "terminal-receipt.json"
    terminal = _load(terminal_path)
    eta_ref = _fraction(terminal["eta_ref_exact"])

    arm_counts: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    moved: dict[str, Counter[str]] = {arm: Counter() for arm in ARMS}
    per_unit: list[dict[str, object]] = []
    divergence: list[dict[str, object]] = []
    horizon: int | None = None
    cumulative = {
        arm: {"bits": Fraction(0), "energy": Fraction(0)} for arm in ARMS
    }

    for receipt in receipts:
        unit = receipt.get("unit")
        trajectories = receipt.get("arms")
        if not isinstance(unit, Mapping) or not isinstance(trajectories, Mapping) or set(trajectories) != set(ARMS):
            raise AttributionError("unit arm coverage is malformed")
        unit_row: dict[str, object] = {"unit": dict(unit), "arms": {}}
        rows_by_arm = {arm: _decision_rows(receipt, arm) for arm in COORDINATOR_ARMS}
        local_horizon = len(rows_by_arm["FULL"])
        if len(rows_by_arm["LITE"]) != local_horizon or horizon not in (None, local_horizon):
            raise AttributionError("decision horizon differs across v1 units")
        horizon = local_horizon
        arm_counts["BASE"]["BASE"] += local_horizon
        moved["BASE"]["0"] += local_horizon
        unit_row["arms"]["BASE"] = {  # type: ignore[index]
            "configuration_types": {"BASE": local_horizon, "unilateral": 0, "evacuation": 0},
            "users_moved": {"0": local_horizon, "1": 0, "unrecoverable_evacuation": 0},
        }
        for arm in COORDINATOR_ARMS:
            local_counts: Counter[str] = Counter()
            local_moved: Counter[str] = Counter()
            for decision in rows_by_arm[arm]:
                profile_id = str(decision.get("selected_profile_id"))
                kind = _kind(profile_id)
                local_counts[kind] += 1
                arm_counts[arm][kind] += 1
                key = "0" if kind == "BASE" else "1" if kind == "unilateral" else "unrecoverable_evacuation"
                local_moved[key] += 1
                moved[arm][key] += 1
            unit_row["arms"][arm] = {  # type: ignore[index]
                "configuration_types": dict(local_counts), "users_moved": dict(local_moved),
            }
        for step in range(local_horizon):
            full = rows_by_arm["FULL"][step]
            lite = rows_by_arm["LITE"][step]
            if full.get("selected_profile_id") != lite.get("selected_profile_id"):
                fn = full.get("selected_nominal")
                ln = lite.get("selected_nominal")
                realised = {
                    arm: trajectories[arm]["steps"][step] for arm in COORDINATOR_ARMS  # type: ignore[index]
                }
                nominal_delta: dict[str, object] | None = None
                if isinstance(fn, Mapping) and isinstance(ln, Mapping):
                    fb = _hex(fn["total_bits_hex"])
                    fe = _hex(fn["total_energy_j_hex"])
                    lb = _hex(ln["total_bits_hex"])
                    le = _hex(ln["total_energy_j_hex"])
                    nominal_delta = {
                        "full_minus_lite_bits": _fp(fb - lb),
                        "full_minus_lite_energy_j": _fp(fe - le),
                        "full_minus_lite_F": _fp((fb - eta_ref * fe) - (lb - eta_ref * le)),
                        "full_minus_lite_served": int(fn["served"]) - int(ln["served"]),
                    }
                divergence.append({
                    "unit": dict(unit), "step_index": step,
                    "full_profile_id": full.get("selected_profile_id"),
                    "lite_profile_id": lite.get("selected_profile_id"),
                    "nominal_delta": nominal_delta,
                    "realised_delta": {
                        "full_minus_lite_bits": _fp(_hex(realised["FULL"]["bits_hex"]) - _hex(realised["LITE"]["bits_hex"])),
                        "full_minus_lite_energy_j": _fp(_hex(realised["FULL"]["energy_j_hex"]) - _hex(realised["LITE"]["energy_j_hex"])),
                        "full_minus_lite_served": int(realised["FULL"]["served"]) - int(realised["LITE"]["served"]),
                    },
                })
        per_unit.append(unit_row)

    assert horizon is not None
    cumulative_rows: list[dict[str, object]] = []
    for step in range(horizon):
        for receipt in receipts:
            trajectories = receipt["arms"]
            for arm in ARMS:
                row = trajectories[arm]["steps"][step]
                cumulative[arm]["bits"] += _hex(row["bits_hex"])
                cumulative[arm]["energy"] += _hex(row["energy_j_hex"])
        eta_base = cumulative["BASE"]["bits"] / cumulative["BASE"]["energy"]
        row: dict[str, object] = {"through_step": step, "arms": {}}
        for arm in ARMS:
            eta = cumulative[arm]["bits"] / cumulative[arm]["energy"]
            advantage = eta / eta_base - 1
            row["arms"][arm] = {  # type: ignore[index]
                "cumulative_eta": _fp(eta), "relative_advantage_vs_base": _fp(advantage),
            }
        cumulative_rows.append(row)

    pooled_counts = Counter()
    pooled_moved = Counter()
    for arm in ARMS:
        pooled_counts.update(arm_counts[arm])
        pooled_moved.update(moved[arm])
    return {
        "schema": SCHEMA, "source_root": str(Path(root).resolve()),
        "terminal_receipt": str(terminal_path.resolve()), "unit_receipts": len(receipts),
        "horizon": horizon, "decisions_per_arm": len(receipts) * horizon,
        "configuration_types": {
            "per_arm": {arm: dict(arm_counts[arm]) for arm in ARMS},
            "pooled_all_arms": dict(pooled_counts),
            "classification": (
                "Selected catalog profile ID. v1 retained catalog aliases, so differently "
                "labelled unilateral/evacuation profiles may execute the same action vector."
            ),
        },
        "users_moved_per_decision": {
            "per_arm": {arm: dict(moved[arm]) for arm in ARMS},
            "pooled_all_arms": dict(pooled_moved),
            "recoverability": (
                "BASE=0 and unilateral=1 are exact from selected_profile_id; evacuation member "
                "counts are not recoverable because v1 receipts retain neither executed action "
                "vectors nor origin membership."
            ),
        },
        "active_beam_counts_per_step": {
            "status": "NOT_RECOVERABLE",
            "reason": (
                "v1 unit receipts contain action-trace digests but not executed action vectors, "
                "physical-key tables, masks, or resolved active-beam sets."
            ),
        },
        "cumulative_ee_advantage_vs_base_by_step": cumulative_rows,
        "full_vs_lite_divergence": {
            "count": len(divergence), "steps": divergence,
            "delta_convention": "FULL_MINUS_LITE; nominal F uses sealed eta_ref",
            "scope": (
                "selected-profile-ID divergence; per-step action-vector divergence is not "
                "recoverable from the v1 aggregate action-trace digests"
            ),
        },
        "per_unit_choice_counts": per_unit,
    }


def markdown(result: Mapping[str, object]) -> str:
    counts = result["configuration_types"]["per_arm"]  # type: ignore[index]
    moved = result["users_moved_per_decision"]["per_arm"]  # type: ignore[index]
    lines = [
        "# C3-S v1 offline attribution", "",
        f"Source: `{result['source_root']}`", "",
        "## Executed configuration types", "",
        "| Arm | BASE | Unilateral | Evacuation |", "|---|---:|---:|---:|",
    ]
    for arm in ARMS:
        row = counts[arm]
        lines.append(f"| {arm} | {row.get('BASE', 0)} | {row.get('unilateral', 0)} | {row.get('evacuation', 0)} |")
    lines.extend(["", str(result["configuration_types"]["classification"])])  # type: ignore[index]
    lines.extend(["", "## Users moved per decision", "", "| Arm | 0 | 1 | Evacuation count unavailable |", "|---|---:|---:|---:|"])
    for arm in ARMS:
        row = moved[arm]
        lines.append(f"| {arm} | {row.get('0', 0)} | {row.get('1', 0)} | {row.get('unrecoverable_evacuation', 0)} |")
    lines.extend([
        "", str(result["users_moved_per_decision"]["recoverability"]),  # type: ignore[index]
        "", "## Active beams", "",
        f"**Not recoverable.** {result['active_beam_counts_per_step']['reason']}",  # type: ignore[index]
        "", "## Cumulative pooled EE advantage vs BASE", "",
        "| Through step | FULL | LITE |", "|---:|---:|---:|",
    ])
    for row in result["cumulative_ee_advantage_vs_base_by_step"]:  # type: ignore[assignment]
        lines.append(
            f"| {row['through_step']} | {100 * row['arms']['FULL']['relative_advantage_vs_base']['float']:.6f}% "
            f"| {100 * row['arms']['LITE']['relative_advantage_vs_base']['float']:.6f}% |"
        )
    divergences = result["full_vs_lite_divergence"]  # type: ignore[assignment]
    lines.extend([
        "", "## FULL vs LITE divergence", "",
        f"Divergent selected-profile IDs: **{divergences['count']}**.", "",
        str(divergences["scope"]), "",
    ])
    if divergences["steps"]:
        lines.extend(["| World | Lineage | Step | FULL | LITE | Nominal ΔF | Realised Δbits | Realised ΔJ |", "|---:|---:|---:|---|---|---:|---:|---:|"])
        for row in divergences["steps"]:
            nominal = row["nominal_delta"]
            delta_f = "n/a" if nominal is None else f"{nominal['full_minus_lite_F']['float']:.6g}"
            realised = row["realised_delta"]
            lines.append(
                f"| {row['unit']['world']} | {row['unit']['lineage']} | {row['step_index']} "
                f"| `{row['full_profile_id']}` | `{row['lite_profile_id']}` | {delta_f} "
                f"| {realised['full_minus_lite_bits']['float']:.6g} | {realised['full_minus_lite_energy_j']['float']:.6g} |"
            )
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = attribute(args.receipts)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="ascii")
        args.output_markdown.write_text(markdown(result), encoding="utf-8")
    except Exception as error:
        print(f"C3S_ATTRIBUTION_ERROR: {error}", file=__import__("sys").stderr)
        return 2
    print(f"C3S_ATTRIBUTION_PASS json={args.output_json} markdown={args.output_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
