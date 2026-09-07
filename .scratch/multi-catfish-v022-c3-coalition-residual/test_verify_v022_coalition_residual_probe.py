"""Independent post-outcome verification tests for the V0.22 result receipt.

These tests consume only the existing JSON result and synthetic in-memory
tamper cases.  They do not start a simulator, load a checkpoint, open TLE, or
run any training split.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULT = REPO / "artifacts" / "multi-catfish-v022-c3-coalition-residual-20260905-r1" / "result.json"
TARGET = HERE / "verify_v022_coalition_residual_probe.py"
SPEC = importlib.util.spec_from_file_location("v022_postoutcome_verifier", TARGET)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _load_result() -> dict[str, object]:
    return json.loads(RESULT.read_text(encoding="ascii"))


def _reseal(payload: dict[str, object]) -> None:
    """Reseal a synthetic payload so tests exercise deeper checks."""

    payload["result_sha256"] = MODULE._canonical_sha256(
        {key: value for key, value in payload.items() if key != "result_sha256"}
    )


def test_existing_result_passes_independent_verification() -> None:
    report = MODULE.verify_result_file(RESULT)

    assert report["status"] == "PASS"
    assert report["recomputed_decision"] == "GO_LC_SRS_OBSERVABILITY_GATE"
    assert report["adoption_profile"] == "11"
    assert report["scan"]["first_qualified"] == {
        "world": 2026121701,
        "step": 1,
    }
    assert all(report["checks"].values())
    assert report["public_good"] == {
        "source_beam_public_good_signature": True,
        "joint_opens_no_new_beam": True,
        "joint_removes_exactly_source_beam": True,
        "pair_served_all_profiles": True,
        "joint_service_noninferior": True,
        "joint_ee_positive": True,
    }


def test_tampered_payload_hash_is_rejected_before_claims_are_used() -> None:
    payload = _load_result()
    payload["profiles"]["11"]["total_bits"] += 1.0  # type: ignore[index]

    with pytest.raises(MODULE.VerificationError, match="result_sha256"):
        MODULE.verify_payload(payload)


def test_resealed_formula_tamper_is_caught_independently_of_mechanics_booleans() -> None:
    payload = copy.deepcopy(_load_result())
    payload["formula"]["z3_bits"][0] += 1.0  # type: ignore[index]
    _reseal(payload)

    with pytest.raises(MODULE.VerificationError, match="formula.z3_bits"):
        MODULE.verify_payload(payload)


def test_resealed_topology_surface_tamper_is_caught_by_recomputation() -> None:
    payload = copy.deepcopy(_load_result())
    # Change an otherwise legal, occupied destination's base score and update
    # both persisted copies of its hash.  The stored proposal is left intact;
    # the independent max/tie-break recomputation must reject it.
    for inputs in (
        payload["topology_inputs"],
        payload["scan"][1]["topology_inputs"],  # type: ignore[index]
    ):
        inputs["base_surface"][27][19] = 100.0  # type: ignore[index]
        inputs["base_surface_sha256"] = hashlib.sha256(
            np.ascontiguousarray(
                np.asarray(inputs["base_surface"], dtype=np.float64),  # type: ignore[index]
                dtype=np.float64,
            ).tobytes()
        ).hexdigest()
    _reseal(payload)

    with pytest.raises(MODULE.VerificationError, match="topology proposal"):
        MODULE.verify_payload(payload)


def test_resealed_public_good_tamper_is_caught_from_profile_beam_sets() -> None:
    payload = copy.deepcopy(_load_result())
    # Keep the record internally well formed while breaking the declared
    # source-beam shutdown signature: add a new beam to the joint profile and
    # also add its satellite to the sorted satellite list.
    payload["profiles"]["11"]["active_beam_keys"].append([70000, 1])  # type: ignore[index]
    payload["profiles"]["11"]["active_satellites"].append(70000)  # type: ignore[index]
    payload["profiles"]["11"]["active_satellites"].sort()  # type: ignore[index]
    payload["profiles"]["11"]["beam_power_w"].append(0.825)  # type: ignore[index]
    _reseal(payload)

    with pytest.raises(MODULE.VerificationError, match="joint_opens_no_new_beam|source_beam"):
        MODULE.verify_payload(payload)


def test_resealed_reported_mechanics_boolean_cannot_override_recomputation() -> None:
    payload = copy.deepcopy(_load_result())
    payload["mechanics"]["joint_removes_exactly_source_beam"] = False  # type: ignore[index]
    _reseal(payload)

    with pytest.raises(MODULE.VerificationError, match="reported mechanics"):
        MODULE.verify_payload(payload)


def test_resealed_composition_tamper_is_caught_by_native_masked_argmax() -> None:
    payload = copy.deepcopy(_load_result())
    payload["composition"]["selected_actions"][27] = 19  # type: ignore[index]
    _reseal(payload)

    with pytest.raises(MODULE.VerificationError, match="selected_actions"):
        MODULE.verify_payload(payload)


def test_optional_verification_output_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "verification.json"
    MODULE.verify_result_file(RESULT, output_path=output)
    assert output.is_file()
    with pytest.raises(MODULE.VerificationError, match="refusing to overwrite"):
        MODULE.verify_result_file(RESULT, output_path=output)
