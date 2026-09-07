from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_c2_v03_merged_history as verifier  # noqa: E402
from verify_c2_v03_resume_parity import exact_differences  # noqa: E402


def _candidate_receipts(elapsed: float, *, passed: bool = True):
    return [
        {
            "candidate_rows": [{"elapsed_s": elapsed, "passed": passed}],
            "episode": 0,
            "step": 1,
        }
    ]


def test_candidate_elapsed_normalization_preserves_scientific_fields():
    left = _candidate_receipts(1.0, passed=True)
    right = _candidate_receipts(9.0, passed=True)
    normalized_left, normalized_right, _ = verifier._normalized_pair(
        "c2-training-receipts.json", left, right
    )
    assert exact_differences(normalized_left, normalized_right) == []

    changed = _candidate_receipts(9.0, passed=False)
    _, normalized_changed, _ = verifier._normalized_pair(
        "c2-training-receipts.json", left, changed
    )
    assert exact_differences(normalized_left, normalized_changed)


def test_main_receipt_normalization_hides_only_three_live_chronology_hashes():
    base = [
        {
            "c2_training": {
                "live_committed": True,
                "primitive_sequence_sha256": "a",
                "transition_sha256": "b",
                "joint_record_sha256": "c",
                "selected_option_id": "stable",
            }
        }
    ]
    changed = copy.deepcopy(base)
    for name in verifier.MAIN_CHRONOLOGY_HASH_FIELDS:
        changed[0]["c2_training"][name] = "changed"
    left, right, _ = verifier._normalized_pair(
        "main-update-receipts.json", base, changed
    )
    assert exact_differences(left, right) == []

    changed[0]["c2_training"]["selected_option_id"] = "wrong"
    _, right, _ = verifier._normalized_pair(
        "main-update-receipts.json", base, changed
    )
    assert exact_differences(left, right)


def _write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def test_merge_receipt_binds_every_history_artifact(tmp_path: Path):
    hashes = {}
    for name in verifier.HISTORY_ARTIFACTS:
        path = tmp_path / name
        _write_json(path, [] if name != "run-telemetry.json" else {})
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {
        "schema": verifier.merger.SCHEMA,
        "status": "PASS",
        "merged_artifact_sha256": hashes,
    }
    _write_json(tmp_path / "merge-receipt.json", receipt)
    assert verifier._verify_merge_receipt(tmp_path)["status"] == "PASS"

    (tmp_path / "episode-logs.json").write_text("[]\n ", encoding="utf-8")
    with pytest.raises(verifier.HistoryParityError, match="hash drifted"):
        verifier._verify_merge_receipt(tmp_path)
