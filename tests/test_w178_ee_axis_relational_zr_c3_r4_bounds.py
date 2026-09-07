"""W-178 -- local R4 comparison-instrument regression checks.

These tests stay on synthetic predecision fixtures.  They do not open a TLE
world, execute an action, fit a learner, or access TEST.  The first two tests
exercise the non-aborting and JSON-finite properties directly; the final test
exercises the complete R4 context report on the retained W173 fixture.
"""

from __future__ import annotations

import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace

import numpy as np


REPO = Path(__file__).resolve().parents[1]
PERF = REPO / ".scratch/multi-catfish-v018-relational-zr/perf"
if str(PERF) not in sys.path:
    sys.path.insert(0, str(PERF))

import verify_v018_r4_cache_equivalence as r4  # noqa: E402


def test_r4_comparison_collects_zero_bound_mismatch_without_nonfinite_json() -> None:
    report = r4._comparison_report(
        left=np.asarray([1.0, 0.0]),
        right=np.asarray([0.0, 0.0]),
        bound=np.asarray([0.0, 0.0]),
    )
    assert report["pass"] is False
    assert report["violation_count"] == 1
    assert report["max_normalized_deviation"] is None
    json.dumps(report, allow_nan=False)


def test_r4_comparison_shape_and_nonfinite_inputs_remain_json_safe() -> None:
    shape = r4._comparison_report(
        left=np.asarray([1.0]),
        right=np.asarray([[1.0]]),
    )
    nonfinite = r4._comparison_report(
        left=np.asarray([np.nan, np.inf]),
        right=np.asarray([0.0, 0.0]),
    )
    assert shape["pass"] is False
    assert nonfinite["pass"] is False
    assert nonfinite["violation_count"] == 2
    r4.canonical_bytes({"shape": shape, "nonfinite": nonfinite})


def test_r4_authenticates_manifest_and_preflight_receipt(tmp_path: Path) -> None:
    source = REPO / "pyproject.toml"
    manifest = tmp_path / "manifest.sha256"
    manifest.write_text(
        f"{r4.file_sha256(source)}  pyproject.toml\n", encoding="utf-8"
    )
    manifest_sha256 = r4.file_sha256(manifest)
    preflight_log = tmp_path / "server-preflight.log"
    preflight_log.write_text("synthetic preflight pass\n", encoding="utf-8")
    preflight_receipt = tmp_path / "server-preflight.receipt"
    preflight_receipt.write_text(
        "\n".join(
            (
                "schema=multi-catfish-mcrl-v018-r4-equivalence-preflight-v1",
                f"manifest_sha256={manifest_sha256}",
                "pytest_exit=0",
                f"log_sha256={r4.file_sha256(preflight_log)}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    closure = r4._authenticate_external_closure(
        code_manifest=manifest,
        code_manifest_sha256=manifest_sha256,
        preflight_receipt=preflight_receipt,
        preflight_log=preflight_log,
    )
    assert closure["code_manifest_sha256"] == manifest_sha256
    assert closure["code_manifest_entry_count"] == 1
    assert closure["preflight_log_sha256"] == r4.file_sha256(preflight_log)


def test_r4_delta_mask_has_focal_victim_axis_and_diagnostic_constants() -> None:
    users = 3
    legal = np.ones((users, 28), dtype=np.bool_)
    focal_axis = np.arange(users, dtype=np.int64)[:, None, None]
    victim_axis = np.arange(users, dtype=np.int64)[None, None, :]
    eligible = legal[:, :, None] & (focal_axis != victim_axis)
    assert eligible.shape == (users, 28, users)
    expected = np.ones((users, 28, users), dtype=np.bool_)
    expected[np.arange(users), :, np.arange(users)] = False
    np.testing.assert_array_equal(eligible, expected)
    assert r4.DELTA_C == 64
    assert r4.DIAGNOSTIC_C == (1, 8, 64, 512, 4096)
    assert r4.DELTA_HARD_CEILING_BITS == 1e-3


def test_r4_w173_context_passes_all_bound_and_exactness_gates() -> None:
    w173 = runpy.run_path(
        str(REPO / "tests/test_w173_ee_axis_relational_zr_c3.py")
    )
    environment, observation, references, opening, powers = w173["_base_fixture"]()
    environment.driver.config = SimpleNamespace(
        ephemeris=SimpleNamespace(time_step_s=1.0)
    )
    report = r4._context_result(
        environment=environment,
        observation=observation,
        references=references,
        background=np.zeros_like(powers),
        required=powers,
        opening=opening,
        workers=1,
    )
    assert report["pass"] is True
    assert report["primitive_checks"]["candidate_rate"]["violation_count"] == 0
    assert report["primitive_checks"]["candidate_interference"]["violation_count"] == 0
    assert report["delta_bound"]["comparison"]["violation_count"] == 0
    assert report["delta_bound"]["hard_ceiling"]["violation_count"] == 0
    assert report["q3_check"]["violation_count"] == 0
    assert report["branch_maps"]["violations"] == 0
    assert report["coupling_coverage"]["changed_key_missing_from_cache"] == 0
    assert report["victim_predicate"]["independent_match"]["violation_count"] == 0
    assert set(report["delta_bound"]["sensitivity"]) == {
        "1",
        "8",
        "64",
        "512",
        "4096",
    }
    json.dumps(report, allow_nan=False)
