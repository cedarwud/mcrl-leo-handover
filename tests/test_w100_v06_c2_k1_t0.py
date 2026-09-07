"""W-100 -- C2-k1 T-0 is a pure recomputation and fails closed."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".scratch" / "c3-v04" / "run_v06_c2_k1_t0.py"
spec = importlib.util.spec_from_file_location("v06_c2_k1_t0", RUNNER)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _trace(base: float) -> dict[str, object]:
    rates_m = [[base + 10.0 * k + float(i) for i in range(3)] for k in range(4)]
    rates_c = [[value + (k + 1.0) for value in row] for k, row in enumerate(rates_m)]
    power_m = [100.0 + k for k in range(4)]
    power_c = [value + 0.001 for value in power_m]
    interval = 2.0
    lam = 3.0
    offsets = [interval * sum(rates_c[k][i] - rates_m[k][i] for i in range(3)) - lam * interval * (power_c[k] - power_m[k]) for k in (1, 2, 3)]
    return {"candidate_rates_bps": rates_c, "reference_rates_bps": rates_m,
            "candidate_system_power_w": power_c, "reference_system_power_w": power_m,
            "interval_s": interval, "lambda_bits_per_j": lam,
            "offset_surplus_bits": offsets}


def _payloads() -> tuple[dict, dict[int, dict], list[float]]:
    anchors = []
    for anchor_id, ref in (("a", 0), ("b", 1)):
        for action in range(28):
            if action == ref:
                continue
            anchors.append({"schema": mod.PHASE_A_ROW_SCHEMA, "row_status": "ready",
                            "sibling_key": [1, anchor_id, "state", 0, [action, 0]],
                            "candidate_action": action, "raw_trace": _trace(float(action))})
    phase_a = {"schema": mod.PHASE_A_SCHEMA, "rows": anchors}
    shards = {}
    for seed in mod.INITIALIZATION_SEEDS:
        rows = []
        for row in anchors:
            copied = dict(row)
            copied["schema"] = mod.PHASE_B_ROW_SCHEMA
            copied["initialization_seed"] = seed
            copied["pair"] = dict(copied.pop("raw_trace")) | {"candidate_action": row["candidate_action"], "reference_action": 0 if row["sibling_key"][1] == "a" else 1}
            rows.append(copied)
        shards[seed] = {"schema": mod.PHASE_B_SHARD_SCHEMA, "rows": rows}
    return phase_a, shards, [1.0, -2.0, 3.0]


def test_recomputes_k1_and_k1_to_k3_without_training_or_selection() -> None:
    phase_a, shards, c3 = _payloads()
    result = mod.compute_diagnostic(phase_a, shards, c3)
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert result["claim_ceiling"] == mod.CLAIM_CEILING
    assert result["training"] is False
    assert result["test_split_opened"] is False
    assert result["outcome_selection"] is False
    assert result["counts"]["anchors"] == 2
    assert result["within_anchor_q13_invariance"]["k1"]["pair_count"] == 6
    assert result["within_anchor_q13_invariance"]["k1_to_k3"]["pair_count"] == 6


def test_tampered_offset_target_fails_closed() -> None:
    phase_a, shards, c3 = _payloads()
    shards[mod.INITIALIZATION_SEEDS[0]]["rows"][0]["pair"]["offset_surplus_bits"][0] += 1.0
    with pytest.raises(mod.DiagnosticError, match="offset_surplus_bits"):
        mod.compute_diagnostic(phase_a, shards, c3)


def test_nan_trace_fails_closed() -> None:
    phase_a, shards, c3 = _payloads()
    shards[mod.INITIALIZATION_SEEDS[1]]["rows"][0]["pair"]["candidate_rates_bps"][1][0] = float("nan")
    with pytest.raises(mod.DiagnosticError, match="finite"):
        mod.compute_diagnostic(phase_a, shards, c3)


def test_missing_initialization_fails_closed() -> None:
    phase_a, shards, c3 = _payloads()
    del shards[mod.INITIALIZATION_SEEDS[-1]]
    with pytest.raises(mod.DiagnosticError, match="all three"):
        mod.compute_diagnostic(phase_a, shards, c3)


def test_write_once_rejects_existing_receipt(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    path.write_bytes(b"sealed")
    with pytest.raises(FileExistsError):
        mod._write_once(path, {"x": 1})
