#!/usr/bin/env python3
"""Independently recompute the six V0.8 Stage-1b primary directions.

This script reads only the packaged result JSON files.  It pools raw episode
rows as sum(bits) / sum(energy), then checks those values against both stored
summary surfaces before reporting the six FULL-versus-drop contrasts.
"""

from __future__ import annotations

from collections import defaultdict
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HA_PATH = ROOT / "evidence" / "v08-stage1b-ha-result.json"
OPS_PATH = ROOT / "evidence" / "v08-stage1b-fable-ops3-reading-result.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rows_by_arm(*payloads: dict) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for payload in payloads:
        for row in payload["rows"]:
            result[str(row["policy_label"])].append(row)
    return result


def ee(rows: list[dict]) -> float:
    return sum(float(row["total_bits"]) for row in rows) / sum(
        float(row["total_energy_j"]) for row in rows
    )


def served(rows: list[dict]) -> float:
    return sum(int(row["served_user_steps"]) for row in rows) / sum(
        int(row["decision_count"]) for row in rows
    )


def select_lineage(rows: list[dict], lineage: int) -> list[dict]:
    return [row for row in rows if int(row["initialization_seed"]) == lineage]


def assert_close(observed: float, expected: float, label: str) -> None:
    if not math.isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-9):
        raise AssertionError(f"{label}: {observed!r} != {expected!r}")


def main() -> None:
    ha = load(HA_PATH)
    ops = load(OPS_PATH)
    grouped = rows_by_arm(ha, ops)
    lineages = [int(value) for value in ha["initialization_seeds"]]

    # P13 is intentionally sourced from the H-A block for the OPS-3 C2
    # contrast.  The OPS-3 result contains only O2/O12/O23/O123 rows.
    required = ("P123", "P13", "P12", "P23", "O123", "O12", "O23")
    for arm in required:
        if arm not in grouped:
            raise AssertionError(f"missing arm {arm}")

    payload_for_arm = {
        **{arm: ha for arm in ("P123", "P13", "P12", "P23")},
        **{arm: ops for arm in ("O123", "O12", "O23")},
    }
    for arm in required:
        payload = payload_for_arm[arm]
        pooled = payload["summaries"]["pooled_by_arm"][arm]
        assert_close(
            ee(grouped[arm]),
            float(pooled["ratio_of_sums_ee_bits_per_j"]),
            f"{arm} pooled EE",
        )
        assert_close(
            served(grouped[arm]),
            float(pooled["served_fraction"]),
            f"{arm} pooled served",
        )
        for lineage in lineages:
            selected = select_lineage(grouped[arm], lineage)
            stored = payload["summaries"]["pooled_by_arm_and_initialization"][arm][
                str(lineage)
            ]
            assert_close(
                ee(selected),
                float(stored["ratio_of_sums_ee_bits_per_j"]),
                f"{arm}/{lineage} EE",
            )
            assert_close(
                served(selected),
                float(stored["served_fraction"]),
                f"{arm}/{lineage} served",
            )

    directions = (
        ("H-A C2", "P123", "P13"),
        ("H-A C3", "P123", "P12"),
        ("H-A C1", "P123", "P23"),
        ("Fable OPS-3 reading C2", "O123", "P13"),
        ("Fable OPS-3 reading C3", "O123", "O12"),
        ("Fable OPS-3 reading C1", "O123", "O23"),
    )
    print("All raw-row pools match pooled_by_arm and pooled_by_arm_and_initialization.")
    for name, left, right in directions:
        pooled = 100.0 * (ee(grouped[left]) / ee(grouped[right]) - 1.0)
        per_lineage = [
            100.0
            * (
                ee(select_lineage(grouped[left], lineage))
                / ee(select_lineage(grouped[right], lineage))
                - 1.0
            )
            for lineage in lineages
        ]
        values = " / ".join(f"{value:+.6f}%" for value in per_lineage)
        print(f"{name}: pooled {pooled:+.6f}%; per lineage {values}")


if __name__ == "__main__":
    main()
