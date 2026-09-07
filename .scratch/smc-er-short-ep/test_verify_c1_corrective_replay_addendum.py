from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_c1_corrective_replay_addendum",
    HERE / "verify_c1_corrective_replay_addendum.py",
)
assert SPEC is not None and SPEC.loader is not None
V = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V
SPEC.loader.exec_module(V)

ADDENDUM = (
    HERE / "C1-CANONICAL-TLE-CORRECTIVE-REPLAY-ADDENDUM-V1-2026-08-28.json"
)


def test_live_addendum_authenticates_same_seed_canonical_tle_chain():
    result = V.verify_addendum(ADDENDUM)
    assert result["status"] == "PASS"
    assert result["failures"] == []
    assert result["build_seed_manifest_count"] == 3
    assert result["build_seed_count"] == 5
    assert result["new_seed_or_sample_selected"] is False
    assert result["outcome_conditioned_selection"] is False


def test_addendum_rejects_outcome_conditioned_replay(tmp_path):
    payload = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(payload)
    tampered["attestations"]["outcome_conditioned_selection"] = True
    path = tmp_path / "tampered-addendum.json"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    result = V.verify_addendum(path)
    assert result["status"] == "FAIL"
    assert "attestations: exact correction boundary mismatch" in result["failures"]
