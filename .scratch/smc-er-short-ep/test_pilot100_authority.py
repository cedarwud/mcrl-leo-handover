from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pilot100_authority", HERE / "pilot100_authority.py"
)
assert SPEC is not None and SPEC.loader is not None
AUTH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUTH
SPEC.loader.exec_module(AUTH)


def _request() -> dict:
    path = AUTH.REPO / AUTH.CANONICAL_AUTHORITY_RELATIVE
    value = json.loads(path.read_text(encoding="utf-8"))
    value["pilot_route_source_sha256"] = {
        relative: AUTH.sha256_file(AUTH.REPO / relative)
        for relative in AUTH.PILOT_ROUTE_SOURCE_PATHS
    }
    return value


def _parent() -> dict:
    corpus = AUTH.REPO / (
        "artifacts/smc-er-c1-authority-20260828/"
        "smc-er-c1-exp-corpus-canonical-tle-20260829-v4/"
        "c1-exp-corpus-manifest.json"
    )
    prereg = AUTH.REPO / "artifacts/PREREG-FROZEN-2026-08-25-R2.json"
    return {
        "status": "PASS",
        "episodes": 1500,
        "learning_rate": 0.001,
        "arms": list(AUTH.ALLOWED_ARMS),
        "authority": {
            "canonical_prereg": str(prereg),
            "canonical_prereg_sha256": AUTH.CANONICAL_PREREG_SHA256,
            "c1_exp_corpus_manifest": str(corpus),
            "c1_exp_corpus_manifest_sha256": AUTH.sha256_file(corpus),
        },
    }


@pytest.fixture(autouse=True)
def fake_parent_validator(monkeypatch):
    calls = []

    def validate(request, *, tle_root, repo):
        calls.append((request, Path(tle_root), Path(repo)))
        return _parent()

    monkeypatch.setattr(AUTH, "validate_intermediate_trend_authority", validate)
    return calls


def test_canonical_request_returns_independent_100ep_authority(fake_parent_validator):
    result = AUTH.validate_pilot100_authority(
        _request(), tle_root=Path("/runtime/tle")
    )
    assert result["status"] == "PASS"
    assert result["episodes"] == 100
    assert result["learning_rate"] == 0.001
    assert result["arms"] == ["B000", "F111", "A011", "A101", "A110"]
    assert result["seeds"] == {
        "training": 2026082911,
        "environment": 2026082912,
        "mobility": 2026082913,
        "evaluation_seeds": [
            2026082914,
            2026082915,
            2026082916,
            2026082917,
            2026082918,
        ],
    }
    assert result["9000_authorized"] is False
    assert result["continuation_rule"]["automatic_longer_run"] is False
    assert len(fake_parent_validator) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("episodes", 101),
        ("learning_rate", 0.01),
        ("9000_authorized", True),
        ("automatic_longer_run_authorized", True),
        ("output_root", "artifacts/other"),
    ],
)
def test_budget_route_and_longer_run_mutations_fail_closed(field, value):
    request = _request()
    request[field] = value
    with pytest.raises(AUTH.Pilot100AuthorityError, match=field):
        AUTH.validate_pilot100_authority(request, tle_root=Path("/runtime/tle"))


def test_seed_arm_and_continuation_mutations_fail_closed():
    cases = []
    seed = _request()
    seed["seeds"]["training"] += 1
    cases.append(seed)
    arm = _request()
    arm["arms"] = list(reversed(arm["arms"]))
    cases.append(arm)
    continuation = _request()
    continuation["continuation_rule"]["automatic_longer_run"] = True
    cases.append(continuation)
    for request in cases:
        with pytest.raises(AUTH.Pilot100AuthorityError):
            AUTH.validate_pilot100_authority(
                request, tle_root=Path("/runtime/tle")
            )


def test_all_four_existing_authorities_are_byte_bound():
    request = _request()
    request["protected_authority_sha256"] = copy.deepcopy(
        request["protected_authority_sha256"]
    )
    key = sorted(request["protected_authority_sha256"])[-1]
    request["protected_authority_sha256"][key] = "0" * 64
    with pytest.raises(AUTH.Pilot100AuthorityError, match="four-authority"):
        AUTH.validate_pilot100_authority(request, tle_root=Path("/runtime/tle"))


def test_pilot_route_source_hash_drift_is_rejected():
    request = _request()
    key = sorted(request["pilot_route_source_sha256"])[0]
    request["pilot_route_source_sha256"][key] = "0" * 64
    with pytest.raises(AUTH.Pilot100AuthorityError, match="pilot route source hash mismatch"):
        AUTH.validate_pilot100_authority(request, tle_root=Path("/runtime/tle"))


def test_absolute_parent_path_is_rejected():
    request = _request()
    request["parent_intermediate_authority"]["path"] = "/tmp/authority.json"
    with pytest.raises(AUTH.Pilot100AuthorityError, match="strict repository-relative"):
        AUTH.validate_pilot100_authority(request, tle_root=Path("/runtime/tle"))
