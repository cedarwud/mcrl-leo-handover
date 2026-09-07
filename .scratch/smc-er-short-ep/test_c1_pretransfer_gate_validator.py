from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "c1_pretransfer_gate_validator",
    HERE / "c1_pretransfer_gate_validator.py",
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)


def test_minimal_self_attested_pass_is_rejected(tmp_path):
    result = tmp_path / "result.json"
    result.write_text(
        json.dumps(
            {
                "schema": "smc-er-pretransfer-consumer-gate-result-v1",
                "source": "C1",
                "gate_type": "pretransfer-representation-and-atomic-bundle",
                "status": "PASS",
                "decision": "ROUTE",
                "prerequisites_closed": True,
                "claim_ceiling": "C1_ATOMIC_TRANSFER_FOR_EXACT_BOUND_DEVELOPMENTAL_RUNNER_ONLY",
                "authority": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(V.C1PretransferGateValidationError) as error:
        V.validate_c1_pretransfer_result(result, rerun_fixtures=False)
    assert any("canonical" in failure or "missing" in failure for failure in error.value.failures)


def test_raw_validator_requires_informative_nonreversing_preference():
    failures: list[str] = []
    V._validate_raw_structure(
        {
            "schema": V.RAW_SCHEMA,
            "status": "complete",
            "claim_ceiling": V.CLAIM_CEILING,
            "checks": {name: True for name in V.EXPECTED_CHECKS},
            "preference_perturbation": {
                "informative": False,
                "non_reversal": True,
                "executed_action": 1,
                "frozen_main_comparator_action": 0,
                "focal_delta": 0.0,
                "atomic_delta": 0.0,
                "direction_product": 0.0,
            },
        },
        failures,
    )
    assert "raw.preference_perturbation: preference reversal/non-informative" in failures


def test_canonical_authority_surface_binds_route_consumer_and_validator():
    authorities = V._canonical_authorities(V.REPO)
    assert authorities["run_short_ep"].name == "run_short_ep.py"
    assert authorities["validator"].name == "c1_pretransfer_gate_validator.py"
    assert authorities["test"].name == "test_c1_pretransfer_consumer_gate.py"
