from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys

import pytest


REPO = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO / ".scratch/multi-catfish-v025-physics-successor/probe/run_v025_matrix_probe.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("v025_matrix_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_dry_run_executes_one_real_step_of_every_declared_arm() -> None:
    result = subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--dry-run"],
        cwd=REPO,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["one_real_step_every_arm"] == payload["arms_expected"]
    assert payload["no_environment_clone"] is True
    assert len(payload["unit_receipt_sha256"]) == 64


def test_estimate_binds_v12_cells_four_worlds_and_shared_rescore() -> None:
    runner = _load_runner()
    payload = runner.estimate(q=1.0)
    assert len(payload["cells"]) == 31
    assert payload["units"] == 124
    assert payload["architecture_tape_once_treatments_rescore"] is True
    assert payload["no_catalogue_or_world_truncation"] is True


def test_cluster_bootstrap_recomputes_pooled_ratio_not_mean_world_ee() -> None:
    runner = _load_runner()
    clusters = (
        {"full_bits": 100.0, "full_joules": 100.0, "comparator_bits": 1.0, "comparator_joules": 1.0, "full_qos": 1.0, "comparator_qos": 1.0, "full_phi": 0.0, "comparator_phi": 0.0, "full_handover_rate": 0.0, "comparator_handover_rate": 0.0},
        {"full_bits": 20.0, "full_joules": 1.0, "comparator_bits": 18.0, "comparator_joules": 1.0, "full_qos": 1.0, "comparator_qos": 0.9, "full_phi": 0.0, "comparator_phi": -1.0, "full_handover_rate": 0.0, "comparator_handover_rate": 1.0},
    )
    result = runner.pooled_ratio_cluster_bootstrap(clusters, draws=256, seed=7)
    expected = 100.0 * (((100.0 + 20.0) / 101.0) / ((1.0 + 18.0) / 2.0) - 1.0)
    mean_world_contrast = 100.0 * (((1.0 + 20.0) / (1.0 + 18.0)) - 1.0)
    assert result["contrast_percentage_points"] == pytest.approx(expected)
    assert result["contrast_percentage_points"] != pytest.approx(mean_world_contrast)
    assert result["estimator"].startswith("paired resample; recompute")


def test_unit_receipt_is_complete_and_write_once(tmp_path: Path) -> None:
    runner = _load_runner()
    receipt = runner.run_unit(setting=runner._setting("a-r0"), world_index=1, executed_steps=1)
    arms = receipt["steps"][0]["arms"]
    assert [row["arm"] for row in arms] == list(runner.ARMS)
    assert receipt["steps"][0]["e1_certificate"]["candidate_census_complete"] is True
    assert receipt["steps"][0]["s0_certificate"]["nominal_information_only"] is True
    assert set(receipt["failure_analysis"]["marginals"]) == {"C1", "C2", "C3"}
    by_arm = {row["arm"]: row for row in arms}
    assert all(row["power_certificate_counts"] for row in arms)
    assert all(0.0 <= row["converged_slow_share"] <= 1.0 for row in arms)
    assert by_arm["NULL"]["configuration_id"] == by_arm["ALL_NEUTRAL_CONTROL"]["configuration_id"]
    assert by_arm["NULL"]["bits"] == by_arm["ALL_NEUTRAL_CONTROL"]["bits"]
    assert by_arm["NULL"]["joules"] == by_arm["ALL_NEUTRAL_CONTROL"]["joules"]
    target = tmp_path / "receipt.json"
    runner.write_immutable(target, receipt)
    assert stat.S_IMODE(target.stat().st_mode) == 0o444
    assert Path(str(target) + ".sha256").is_file()
    with pytest.raises(runner.ProbeError):
        runner.write_immutable(target, receipt)
