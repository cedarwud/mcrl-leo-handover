#!/usr/bin/env python3
"""Measure V0.23 source residual recomputation drift without changing evidence."""

from __future__ import annotations

import argparse
import gc
import importlib.util
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
VERIFIER = HERE / "verify_v023_lcsrs_scientific.py"
FIELDS = {
    "G profile",
    "formula_own_bits",
    "formula_nonfocal_bits",
    "formula_d_bits",
    "formula_joint_delta_bits",
    "formula_joint_delta_energy_j",
    "formula_joint_surplus_bits",
    "formula_interaction_bits",
    "formula_interaction_energy_j",
    "formula_interaction_surplus_bits",
    "formula_equal_share_bits",
    "z3_bits_by_draw",
    "z3_normalized_by_draw",
    "formula_identity_residual_bits",
    "pair target by draw",
}


def _load_verifier():
    spec = importlib.util.spec_from_file_location("v023_residual_diagnosis_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load verifier: {VERIFIER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs=8, type=Path, required=True)
    args = parser.parse_args()

    verifier = _load_verifier()
    original = verifier._assert_numeric_equal
    active: list[tuple[str, float, float, float, float]] = []

    def audit(actual: object, expected: object, *, field: str) -> None:
        if field not in FIELDS:
            original(actual, expected, field=field)
            return
        left_array = np.asarray(actual, dtype=np.float64)
        right_array = np.asarray(expected, dtype=np.float64)
        if left_array.shape != right_array.shape:
            original(actual, expected, field=field)
        for left, right in zip(left_array.reshape(-1), right_array.reshape(-1), strict=True):
            scale = max(1.0, abs(float(left)), abs(float(right)))
            tolerance = max(1.0e-12, 1024.0 * np.finfo(np.float64).eps * scale)
            active.append((field, float(left), float(right), abs(float(left - right)), tolerance))

    verifier._assert_numeric_equal = audit
    summaries: dict[str, dict[str, object]] = {}
    total_rows = 0
    total_mismatches = 0
    worst: tuple[int, str, float, float, float, float] | None = None
    for path in args.source:
        active.clear()
        result = verifier.verify_source_world_science(path.resolve())
        for field, left, right, delta, tolerance in active:
            total_rows += 1
            total_mismatches += int(delta > tolerance)
            summary = summaries.setdefault(
                field,
                {"values": 0, "mismatches": 0, "max_delta": 0.0, "max_ratio": 0.0},
            )
            summary["values"] = int(summary["values"]) + 1
            summary["mismatches"] = int(summary["mismatches"]) + int(delta > tolerance)
            summary["max_delta"] = max(float(summary["max_delta"]), delta)
            summary["max_ratio"] = max(float(summary["max_ratio"]), delta / tolerance)
            candidate = (int(result["world"]), field, left, right, delta, tolerance)
            if worst is None or delta / tolerance > worst[4] / worst[5]:
                worst = candidate
        print(
            "WORLD",
            result["world"],
            "ROWS",
            len(active),
            "MISMATCHES",
            sum(delta > tolerance for _, _, _, delta, tolerance in active),
            "MAX_DELTA",
            max((delta for _, _, _, delta, _ in active), default=0.0),
            "MAX_RATIO",
            max((delta / tolerance for _, _, _, delta, tolerance in active), default=0.0),
            flush=True,
        )
        del result
        gc.collect()
    print("TOTAL_ROWS", total_rows)
    print("TOTAL_MISMATCHES", total_mismatches)
    for field in sorted(FIELDS):
        summary = summaries.get(field)
        if summary is None:
            continue
        print(
            "FIELD",
            field,
            "VALUES",
            summary["values"],
            "MISMATCHES",
            summary["mismatches"],
            "MAX_DELTA",
            summary["max_delta"],
            "MAX_RATIO",
            summary["max_ratio"],
        )
    if worst is None:
        raise RuntimeError("diagnosis observed no numeric rows")
    print(
        "WORST",
        "world",
        worst[0],
        "field",
        worst[1],
        "stored",
        worst[2].hex(),
        "recomputed",
        worst[3].hex(),
        "delta",
        worst[4],
        "tolerance",
        worst[5],
        "ratio",
        worst[4] / worst[5],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
