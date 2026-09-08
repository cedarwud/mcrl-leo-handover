"""Deterministic arithmetic replay of 200 C1 and 200 C2 stored labels."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
TARGET_ROOT = Path("/home/sat/mcrl-v023-c1c2-targets-20260907-ops3-r8")
COUNT = 200


def number(value: Any) -> float:
    return float.fromhex(value) if isinstance(value, str) and value.startswith(("0x", "-0x")) else float(value)


def sampled_rows(kind: str):
    paths = sorted(TARGET_ROOT.glob(f"{kind}-*-world-*.json"))
    if len(paths) != 16:
        raise RuntimeError(f"expected 16 {kind} shards, found {len(paths)}")
    base, extra = divmod(COUNT, len(paths))
    for file_index, path in enumerate(paths):
        payload = json.loads(path.read_text())
        rows = payload["rows"]
        take = base + (file_index < extra)
        indices = np.linspace(0, len(rows) - 1, take, dtype=int)
        for index in indices.tolist():
            yield path, index, payload, rows[index]


def compare(observed: float, expected: float) -> tuple[float, float]:
    absolute = abs(observed - expected)
    relative = absolute / max(abs(expected), np.finfo(float).tiny)
    return absolute, relative


def replay_c1() -> dict[str, Any]:
    maxima = {"zeta1": [0.0, 0.0, None], "zeta3": [0.0, 0.0, None], "identity": [0.0, 0.0, None]}
    mismatches = []
    count = 0
    for path, index, _payload, row in sampled_rows("c1"):
        raw, targets = row["raw"], row["targets"]
        interval = number(raw["interval_s"])
        multiplier = number(raw["lambda_bits_per_j"])
        focal = int(raw["focal_user"])
        candidate_rates = np.array([number(v) for v in raw["candidate_rates_bps"]])
        reference_rates = np.array([number(v) for v in raw["reference_rates_bps"]])
        delta = candidate_rates - reference_rates
        delta_energy = interval * (
            number(raw["candidate_system_power_w"]) - number(raw["reference_system_power_w"])
        )
        zeta1 = interval * float(delta[focal]) - multiplier * delta_energy
        zeta3 = interval * math.fsum(float(v) for i, v in enumerate(delta) if i != focal)
        total = interval * math.fsum(float(v) for v in delta) - multiplier * delta_energy
        identity = math.fsum((zeta1, zeta3)) - total
        values = {
            "zeta1": (number(targets["zeta1_focal_surplus_bits"]), zeta1),
            "zeta3": (number(targets["zeta3_nonfocal_externality_bits"]), zeta3),
            "identity": (number(targets["identity_residual_bits"]), identity),
        }
        for name, (stored, rebuilt) in values.items():
            absolute, relative = compare(stored, rebuilt)
            if absolute > maxima[name][0]:
                maxima[name] = [absolute, relative, {"file": path.name, "row": index, "stored": stored, "recomputed": rebuilt}]
            tolerance = max(1e-3, 1024 * np.finfo(float).eps * max(abs(stored), abs(rebuilt), 1.0))
            if absolute > tolerance and len(mismatches) < 10:
                mismatches.append({"term": name, "file": path.name, "row": index, "absolute_error": absolute})
        count += 1
    return {"count": count, "maxima": maxima, "mismatch_count_capped": len(mismatches), "mismatches": mismatches}


def replay_c2() -> dict[str, Any]:
    maxima = {name: [0.0, 0.0, None] for name in ("candidate", "reference", "delta")}
    mismatches = []
    count = 0
    stale_default_rows_differing = 0
    stale_lambda = float.fromhex("0x1.443a8f481639ap+26")
    for path, index, payload, row in sampled_rows("c2"):
        multiplier = number(payload["lambda_bits_per_j"])
        kappa = number(payload["kappa_bits"])
        horizon = int(row["horizon"])
        legal = np.asarray(row["action_mask"], dtype=bool)
        persistence = np.asarray(row["persistence"], dtype=float)[:horizon]
        rates = np.asarray(row["rate_bps"], dtype=float)[:horizon]
        marginal = np.asarray(row["marginal_power_w"], dtype=float)[:horizon]
        interval = float.fromhex("0x1.e147ae147ae15p+4")

        def surface(lam: float) -> np.ndarray:
            if horizon == 0:
                return np.zeros(legal.shape, dtype=float)
            terms = persistence * interval * (rates - lam * marginal) - (1.0 - persistence) * kappa
            z = terms.sum(axis=0) / horizon
            q = (z - z[int(row["q1_reference_action"])]) / kappa
            return np.where(legal, q, 0.0)

        q = surface(multiplier)
        old_q = surface(stale_lambda)
        candidate = float(q[int(row["candidate_action"])])
        reference = float(q[int(row["reference_action"])])
        delta = candidate - reference
        if not np.array_equal(q, old_q):
            stale_default_rows_differing += 1
        values = {
            "candidate": (number(row["target_candidate_value"]), candidate),
            "reference": (number(row["target_reference_value"]), reference),
            "delta": (number(row["target_delta"]), delta),
        }
        for name, (stored, rebuilt) in values.items():
            absolute, relative = compare(stored, rebuilt)
            if absolute > maxima[name][0]:
                maxima[name] = [absolute, relative, {"file": path.name, "row": index, "stored": stored, "recomputed": rebuilt}]
            tolerance = max(1e-12, 1024 * np.finfo(float).eps * max(abs(stored), abs(rebuilt), 1.0))
            if absolute > tolerance and len(mismatches) < 10:
                mismatches.append({"term": name, "file": path.name, "row": index, "absolute_error": absolute})
        count += 1
    return {
        "count": count,
        "maxima": maxima,
        "mismatch_count_capped": len(mismatches),
        "mismatches": mismatches,
        "rows_that_change_under_stale_default": stale_default_rows_differing,
    }


def main() -> None:
    result = {
        "schema": "v023-target-replay-v1",
        "selection": "sorted 16 mode-by-world shards; 12/13 evenly spaced rows per shard",
        "c1": replay_c1(),
        "c2": replay_c2(),
        "limitation": (
            "Stored rows contain derived rates/powers but not ECEF geometry and fading variates; "
            "therefore physical observables cannot be regenerated solely from stored state vectors."
        ),
    }
    (HERE / "part3-target-replay.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
