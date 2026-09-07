"""W-39 — prospective G-C2 multi-seed gate adjudication."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = ROOT / ".scratch" / "ee-axis-redesign"
if str(GATE_DIR) not in sys.path:
    sys.path.insert(0, str(GATE_DIR))

import run_c2_v03_keyed_multiseed_gate as gate  # noqa: E402
import run_c2_v03_deterministic_plumbing_probe as probe  # noqa: E402


def _prereg():
    return json.loads(
        (ROOT / "artifacts/c2-v03-gate-20260831/prereg.json").read_text()
    )


def _row(seed: int, index: int, *, positive: bool = False, safe: bool = True):
    return {
        "seed": seed,
        "outcome": "COMPLETE_TRACE_SCORED",
        "anchor_schedule_sha256": f"{seed:08d}-{index // 2}",
        "service_guard": {"passed": safe},
        "positive_service_safe": bool(positive and safe),
    }


def _seed_result(seed: int, *, positive: bool = False, attempts: int = 6):
    rows = [_row(seed, index, positive=positive and index == 0) for index in range(attempts)]
    return {
        "seed": seed,
        "anchors_scheduled": 3 if attempts >= 6 else 1,
        "attempts_scheduled": attempts,
        "rows": rows,
    }


def test_four_of_five_positive_seed_worlds_authorize_only_bounded_pilot():
    seeds = [2026083101, 2026083102, 2026083103, 2026083104, 2026083105]
    results = [
        _seed_result(seed, positive=index < 4)
        for index, seed in enumerate(seeds)
    ]

    decision = gate._adjudicate(_prereg(), results)

    assert decision["outcome"] == "GO_BOUNDED_LEARNABILITY_PILOT_ONLY"
    assert decision["positive_seeds"] == seeds[:4]
    assert decision["attempts"] == 30
    assert decision["coverage_ok"] is True
    assert decision["completion_ok"] is True


def test_positive_headroom_in_only_three_seed_worlds_is_scientific_no_go():
    seeds = [2026083101, 2026083102, 2026083103, 2026083104, 2026083105]
    results = [
        _seed_result(seed, positive=index < 3)
        for index, seed in enumerate(seeds)
    ]

    decision = gate._adjudicate(_prereg(), results)

    assert decision["outcome"] == "SCIENTIFIC_NO_GO"
    assert decision["positive_ok"] is False


def test_insufficient_per_seed_coverage_is_indeterminate_not_a_negative_result():
    seeds = [2026083101, 2026083102, 2026083103, 2026083104, 2026083105]
    results = [_seed_result(seed, positive=True) for seed in seeds]
    results[-1] = _seed_result(seeds[-1], positive=True, attempts=3)

    decision = gate._adjudicate(_prereg(), results)

    assert decision["outcome"] == "INDETERMINATE"
    assert decision["coverage_ok"] is False


def test_any_instrument_error_fails_the_gate():
    seeds = [2026083101, 2026083102, 2026083103, 2026083104, 2026083105]
    results = [_seed_result(seed, positive=True) for seed in seeds]
    results[0]["rows"][0] = {
        "seed": seeds[0],
        "outcome": "INSTRUMENT_ERROR_NOT_SCORED",
        "error_class": "RuntimeError",
        "error": "sealed sentinel",
    }

    decision = gate._adjudicate(_prereg(), results)

    assert decision["outcome"] == "INSTRUMENT_FAIL"
    assert decision["instrument_errors"] == 1


def test_trace_receipt_service_guard_detects_a_new_downstream_outage():
    def step(offset: int, served: tuple[bool, bool]):
        return SimpleNamespace(
            offset=offset,
            link_rate_bps=(10.0, 20.0),
            system_power_w=100.0,
            served=served,
        )

    reference = [step(offset, (True, True)) for offset in range(4)]
    candidate = [step(0, (True, True)), step(1, (True, False)), step(2, (True, True)), step(3, (True, True))]

    receipts, z2, service_guard = probe._trace_receipts(
        reference,
        candidate,
        interval_s=1.0,
        multiplier=1.0,
        focal_user=0,
    )

    assert z2 == 0.0
    assert receipts[1]["new_outage_users"] == [1]
    assert service_guard["passed"] is False
    assert service_guard["no_new_outage_for_any_reference_served_user"] is False
