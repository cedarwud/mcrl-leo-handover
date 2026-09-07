"""W-98 -- independent persisted V0.5 controlled-tape hard gate."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFY_PATH = ROOT / ".scratch/c3-v04/verify_v05_c2_controlled_tape_mechanics.py"
_SPEC = importlib.util.spec_from_file_location("v05_c2_mechanics_verifier", VERIFY_PATH)
assert _SPEC is not None and _SPEC.loader is not None
verifier = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verifier)


OUTPUT_DIR = ROOT / "artifacts/multi-catfish-v05-c2-controlled-tape-mechanics-20260901-r4"
SCHEDULE = ROOT / "artifacts/multi-catfish-v04-c2-support-complete-census-20260901-r3/schedule.json"
PREPARE = ROOT / "artifacts/multi-catfish-v04-c2-support-complete-census-20260901-r3/prepare-receipt.json"
Q13_GATE = ROOT / "artifacts/multi-catfish-v04-c3-learnability-20260901-r2/result.json"


def _batch_kwargs(*, main: Path | None = None) -> dict[str, object]:
    return {
        "main_path": main or OUTPUT_DIR / "main.json",
        "q13_paths": [OUTPUT_DIR / f"q13-{seed}.json" for seed in (2026092101, 2026092102, 2026092103)],
        "schedule_path": SCHEDULE,
        "prepare_receipt_path": PREPARE,
        "q13_gate_path": Q13_GATE,
    }


def test_real_r4_batch_passes_48_row_mechanics_only() -> None:
    pytest.importorskip("torch")
    receipt = verifier.verify_lockstep_batch(**_batch_kwargs())

    assert receipt["status"] == "PASS_MECHANICS_ONLY"
    assert receipt["row_count"] == 48
    assert receipt["target_signs_inspected"] is False
    assert receipt["training_run"] is False
    assert receipt["test_split_opened"] is False
    assert receipt["held_out_ee_evaluated"] is False


def test_tampered_nonfocal_receipt_fails_closed(tmp_path: Path) -> None:
    source = OUTPUT_DIR / "main.json"
    payload = json.loads(source.read_text(encoding="ascii"))
    payload["rows"][0]["pair_plan"]["steps"][0]["nonfocal_equal"] = False
    tampered = tmp_path / "main-tampered.json"
    tampered.write_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n"
    )

    with pytest.raises(verifier.MechanicsVerificationError, match="nonfocal_equal"):
        verifier.verify_lockstep_batch(**_batch_kwargs(main=tampered))
