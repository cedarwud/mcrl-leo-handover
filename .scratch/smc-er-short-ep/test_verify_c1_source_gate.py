from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_c1_source_gate", HERE / "verify_c1_source_gate.py"
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)

SOURCE_RESULT = Path(
    "/tmp/smc-er-c1-source-gate-a-canonical-tle-20260828-v3/"
    "c1-source-gate-a-result.json"
)
CORRECTIVE_ADDENDUM = (
    HERE / "C1-CANONICAL-TLE-CORRECTIVE-REPLAY-ADDENDUM-V1-2026-08-28.json"
)
CORRECTIVE_VERIFICATION = Path(
    "/tmp/c1-canonical-tle-corrective-replay-verification-v1.json"
)
SEED_PROVENANCE_CORRECTION = (
    HERE
    / "C1-SOURCE-GATE-A-SEED-PROVENANCE-CORRECTION-V1-2026-08-28.json"
)


def test_verifier_fails_on_paired_delta_tamper():
    payload = {
        "schema": V.gate.RESULT_SCHEMA,
        "authority": {
            "method_sha256": V.gate.sha256_file(V.gate.METHOD),
            "spec_sha256": V.gate.sha256_file(V.gate.SPEC),
            "runner_sha256": V.gate.sha256_file(V.gate.HERE / "run_c1_source_gate.py"),
            "checkpoint_path": str(V.gate.METHOD),
            "checkpoint_sha256": V.gate.sha256_file(V.gate.METHOD),
            "seed_manifest_path": str(V.gate.SPEC),
            "seed_manifest_sha256": V.gate.sha256_file(V.gate.SPEC),
        },
        "paired_rows": [],
        "seed_rows": [],
        "result": {},
    }
    result = V.verify_payload(copy.deepcopy(payload))
    assert result["status"] == "FAIL"
    assert "seed_step_denominator_mismatch" in result["failures"]


def test_live_verifier_binds_manifest_order_and_corrective_replay():
    payload = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    result = V.verify_payload(
        payload,
        source_gate_path=SOURCE_RESULT,
        corrective_addendum=CORRECTIVE_ADDENDUM,
        corrective_replay_verification=CORRECTIVE_VERIFICATION,
        source_seed_provenance_correction=SEED_PROVENANCE_CORRECTION,
        replay_raw_rows=False,
    )
    assert result["status"] == "PASS"
    assert result["manifest_to_paired_rows_order_equal"] is True
    assert result["manifest_to_seed_rows_order_equal"] is True
    assert result["corrective_replay_verification_equal"] is True
    assert result["source_seed_provenance_correction_equal"] is True


def test_live_verifier_rejects_manifest_to_row_reordering():
    payload = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    payload["paired_rows"][0], payload["paired_rows"][1] = (
        payload["paired_rows"][1],
        payload["paired_rows"][0],
    )
    result = V.verify_payload(
        payload,
        source_gate_path=SOURCE_RESULT,
        corrective_addendum=CORRECTIVE_ADDENDUM,
        corrective_replay_verification=CORRECTIVE_VERIFICATION,
        source_seed_provenance_correction=SEED_PROVENANCE_CORRECTION,
        replay_raw_rows=False,
    )
    assert result["status"] == "FAIL"
    assert "manifest_to_paired_rows_order_mismatch" in result["failures"]


def test_live_verifier_rejects_seed_correction_tamper(tmp_path):
    payload = json.loads(SOURCE_RESULT.read_text(encoding="utf-8"))
    correction = json.loads(SEED_PROVENANCE_CORRECTION.read_text(encoding="utf-8"))
    correction["transparent_reconstruction"]["spec_sha256_hex_character_offsets"][-1] = 32
    tampered = tmp_path / "tampered-seed-correction.json"
    tampered.write_text(json.dumps(correction), encoding="utf-8")
    result = V.verify_payload(
        payload,
        source_gate_path=SOURCE_RESULT,
        corrective_addendum=CORRECTIVE_ADDENDUM,
        corrective_replay_verification=CORRECTIVE_VERIFICATION,
        source_seed_provenance_correction=tampered,
        replay_raw_rows=False,
    )
    assert result["status"] == "FAIL"
    assert (
        "source_seed_provenance_correction_reconstruction_mismatch"
        in result["failures"]
    )
