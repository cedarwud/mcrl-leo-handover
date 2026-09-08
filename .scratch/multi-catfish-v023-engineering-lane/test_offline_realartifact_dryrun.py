from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOL = HERE / "offline_realartifact_dryrun.py"
REAL = HERE / "fixtures/real-artifact"


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *arguments],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def test_complete_chain_passes_and_preserves_exact_input_identity(tmp_path: Path):
    before = hashlib.sha256((REAL / "payload.txt").read_bytes()).hexdigest()
    output = tmp_path / "pass-output"
    completed = _run(
        "--spec", str(HERE / "specs/selftest_dryrun.json"),
        "--repo", str(REPO),
        "--output", str(output),
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert completed.stdout.strip().splitlines()[-1] == "DRYRUN_SELFTEST_CHAIN_PASS"
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    assert report["claim_ceiling"] == "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
    assert report["scientific_output"] is False
    assert report["verdict"] == "PASS"
    assert [step["status"] for step in report["steps"]] == ["PASS"] * 11
    assert report["wall_s"] >= 0.0
    assert all(step["wall_s"] >= 0.0 for step in report["steps"])
    assert report["wall_s"] >= sum(step["wall_s"] for step in report["steps"])
    identity = report["input_identities"]["real_root"]
    assert identity["path"] == str(REAL.resolve())
    assert identity["sha256"] == report["input_integrity"]["real_root"]["after"]["sha256"]
    assert hashlib.sha256((REAL / "payload.txt").read_bytes()).hexdigest() == before
    assert (output / "checkpoint.txt").read_text(encoding="ascii") == "1"


def test_mutation_is_blocked_dependencies_block_and_later_step_runs(tmp_path: Path):
    before = (REAL / "payload.txt").read_bytes()
    spec = {
        "schema": "multi-catfish-v023-offline-realartifact-chain-spec-v1",
        "name": "MUTATION_NEGATIVE",
        "artifacts": [{"name": "real_root", "path": str(REAL)}],
        "modules": {"fixture": {"path": str(HERE / "fixtures/dryrun_chain.py"), "name": "dryrun_chain"}},
        "steps": [
            {
                "name": "forbidden_write",
                "callable": {"module": "fixture", "name": "attempt_input_write"},
                "args": [{"artifact": "real_root"}],
                "inputs": ["real_root"],
            },
            {
                "name": "blocked_dependent",
                "callable": {"module": "fixture", "name": "consume_missing"},
                "args": [{"result": "forbidden_write"}],
            },
            {
                "name": "independent_after_failure",
                "callable": {"module": "fixture", "name": "authenticate"},
                "args": [{"artifact": "real_root"}],
                "inputs": ["real_root"],
            },
        ],
    }
    spec_path = tmp_path / "mutation.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "mutation-output"
    completed = _run("--spec", str(spec_path), "--repo", str(REPO), "--output", str(output))
    assert completed.returncode == 2
    assert completed.stdout.strip().splitlines()[-1] == "DRYRUN_MUTATION_NEGATIVE_FAIL"
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    assert [step["status"] for step in report["steps"]] == ["FAIL", "BLOCKED", "PASS"]
    assert "blocked write into input artifact" in report["steps"][0]["exception"]["text"]
    assert (REAL / "payload.txt").read_bytes() == before
    assert report["input_integrity"]["real_root"]["status"] == "PASS"


def test_missing_module_and_artifact_are_blocked(tmp_path: Path):
    spec = {
        "schema": "multi-catfish-v023-offline-realartifact-chain-spec-v1",
        "name": "LAZY_MISSING",
        "artifacts": [{"name": "future", "path": str(tmp_path / "future-root")}],
        "modules": {"future": {"path": str(tmp_path / "future.py"), "name": "future"}},
        "steps": [
            {"name": "module_missing", "callable": {"module": "future", "name": "load"}},
            {"name": "artifact_missing", "callable": {"module": "future", "name": "load"}, "args": [{"artifact": "future"}]},
        ],
    }
    spec_path = tmp_path / "missing.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "missing-output"
    completed = _run("--spec", str(spec_path), "--repo", str(REPO), "--output", str(output))
    assert completed.returncode == 3
    assert completed.stdout.strip().splitlines()[-1] == "DRYRUN_LAZY_MISSING_BLOCKED"
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    assert [step["status"] for step in report["steps"]] == ["BLOCKED", "BLOCKED"]


def test_missing_binder_output_prints_requires_after_reason(tmp_path: Path):
    reason = (
        "bind_v023_c1c2_successor_freeze.py --write produces this artifact; "
        "run the Stage-A gate after bind and before the launcher"
    )
    spec = {
        "schema": "multi-catfish-v023-offline-realartifact-chain-spec-v1",
        "name": "BINDER_ORDER",
        "artifacts": [{
            "name": "binder_output",
            "path": str(tmp_path / "not-bound-yet.json"),
            "requires_after": reason,
        }],
        "modules": {
            "fixture": {"path": str(HERE / "fixtures/dryrun_chain.py"), "name": "dryrun_chain"}
        },
        "steps": [{
            "name": "needs_binder_output",
            "callable": {"module": "fixture", "name": "consume_missing"},
            "args": [{"artifact": "binder_output"}],
        }],
    }
    spec_path = tmp_path / "binder-order.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    output = tmp_path / "binder-order-output"
    completed = _run("--spec", str(spec_path), "--repo", str(REPO), "--output", str(output))
    assert completed.returncode == 3, completed.stderr + completed.stdout
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    step = report["steps"][0]
    assert step["status"] == "BLOCKED"
    assert step["exception"]["text"].endswith(f"requires_after: {reason}")


def test_list_real_artifacts_reports_present_and_missing(tmp_path: Path):
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps({"artifacts": [
        {"name": "present", "path": str(REAL)},
        {"name": "missing", "path": str(tmp_path / "missing")},
    ]}), encoding="utf-8")
    completed = _run("--list-real-artifacts", str(candidates))
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    by_name = {entry["name"]: entry for entry in payload["artifacts"]}
    assert by_name["present"]["status"] == "PRESENT"
    assert by_name["present"]["sha256"]
    assert by_name["missing"]["status"] == "MISSING"
