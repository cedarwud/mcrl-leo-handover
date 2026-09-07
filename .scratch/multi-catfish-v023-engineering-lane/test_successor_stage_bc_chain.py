from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import torch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TOOL = HERE / "offline_realartifact_dryrun.py"
SPEC = HERE / "specs/successor_stage_bc_chain.json"
PHYSICAL = REPO / ".scratch/multi-catfish-v023-c1c2-successor-physical-evaluation"
MODEL = REPO / ".scratch/multi-catfish-v023-two-route-source-training-runner"
for path in (HERE, REPO / "src", PHYSICAL, MODEL):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import dryrun_support
import ee_axis_two_route_model as model
import v023_c1c2_successor_physical_runner as runner
import v023_c1c2_successor_plumbing_diagnostic as diagnostic


def _run(spec: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), "--repo", str(REPO), "--spec", str(spec), "--output", str(output)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def test_stage_bc_default_status_matrix(tmp_path: Path) -> None:
    output = tmp_path / "stage-bc"
    completed = _run(SPEC, output)
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    statuses = {step["name"]: step["status"] for step in report["steps"]}
    for name in (
        "fresh_exports",
        "load_exports_both_paths",
        "world_plan_build_check",
        "simulate_off_deployment",
        "receipt_cadence_resume",
    ):
        assert statuses[name] == "PASS"
    assert statuses["baseline_admission"] == "PASS"
    assert statuses["optional_real_world"] == "BLOCKED"
    assert completed.returncode == 3, completed.stderr + completed.stdout
    assert completed.stdout.strip().splitlines()[-1] == "DRYRUN_successor_stage_bc_BLOCKED"
    assert report["claim_ceiling"] == "ENGINEERING_LANE_READ_ONLY_NO_SCIENTIFIC_OUTPUT"
    assert report["scientific_output"] is False
    assert not (output / "physical-cadence/result.json").exists()
    assert (output / "physical-cadence/checkpoints/checkpoint-000100.json").is_file()
    assert (output / "physical-cadence/rungs/rung-000100.json").is_file()


def test_stage_bc_missing_module_is_lazy_blocked(tmp_path: Path) -> None:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    payload["modules"]["runner"]["path"] = ".scratch/not-yet-present/runner.py"
    payload["modules"]["runner"]["name"] = "not_yet_present_runner"
    for artifact in payload["artifacts"]:
        if artifact["name"] in {"baseline_checkpoint", "baseline_status"}:
            artifact["path"] = ".scratch/not-yet-present/" + artifact["name"]
    spec = tmp_path / "lazy-stage-bc.json"
    spec.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "lazy-output"
    completed = _run(spec, output)
    assert completed.returncode == 3, completed.stderr + completed.stdout
    report = json.loads((output / "dryrun-report.json").read_text(encoding="ascii"))
    statuses = {step["name"]: step["status"] for step in report["steps"]}
    assert statuses["fresh_exports"] == "PASS"
    assert statuses["load_exports_both_paths"] == "BLOCKED"
    assert statuses["world_plan_build_check"] == "PASS"
    assert statuses["simulate_off_deployment"] == "BLOCKED"
    assert statuses["receipt_cadence_resume"] == "BLOCKED"


def test_owned_specs_pass_authenticated_model_config_digest() -> None:
    stage_bc = json.loads(SPEC.read_text(encoding="utf-8"))
    fresh = stage_bc["steps"][0]
    assert fresh["kwargs"]["model_config_sha256"] == {
        "module_constant": {"module": "model", "name": "FROZEN_MODEL_CONFIG_SHA256"}
    }

    stage_a_path = HERE / "specs/successor_stage_a_chain.json"
    stage_a = json.loads(stage_a_path.read_text(encoding="utf-8"))
    orchestrator = next(
        step for step in stage_a["steps"] if step["name"] == "orchestrator_config"
    )
    assert orchestrator["kwargs"]["model_config_sha256"] == {
        "sha256": {"artifact": "model_config"}
    }


def test_step_two_rejects_forged_q3_export(tmp_path: Path) -> None:
    bundle = dryrun_support.build_fresh_two_route_exports(
        REPO / ".scratch/multi-catfish-v023-c1c2-successor/V023-C1C2-SUCCESSOR-MODEL-CONFIG.json",
        tmp_path / "exports",
        seed=2927175120652069826,
        model_config_sha256=model.FROZEN_MODEL_CONFIG_SHA256,
        arms=("FULL2", "DROP_C1", "DROP_C2"),
        model_class=model.EEAxisTwoRouteModel,
        model_config_class=model.EEAxisTwoRouteConfig,
        q1_config_class=model.EEAxisActionSharedConfig,
        q2_config_class=model.EEAxisV014HeadConfig,
    )
    exports = bundle["exports"]
    assert {item["seed"] for item in exports} == {model.FORMAL_TRAIN_SEED}
    assert len({item["initialization"]["bytes_sha256"] for item in exports}) == 1
    assert len({item["sha256"] for item in exports}) == 3
    forged_bundle = copy.deepcopy(bundle)
    forged = forged_bundle["exports"][0]
    path = Path(forged["path"])
    payload = torch.load(path, map_location="cpu", weights_only=False)
    payload["q3"] = {"state": "forbidden"}
    torch.save(payload, path)
    forged["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(runner.C1C2PhysicalError, match="Q3/C3"):
        dryrun_support.load_exports_through_both_paths(
            forged_bundle,
            physical_loader=runner.load_learned_two_route_checkpoint,
            diagnostic_loader=diagnostic.runner.load_learned_two_route_checkpoint,
        )
