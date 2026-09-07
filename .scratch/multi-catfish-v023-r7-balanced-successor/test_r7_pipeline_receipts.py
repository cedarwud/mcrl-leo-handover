"""Synthetic R7 pipeline receipts; never import a simulator or fit a learner."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gate = _load("r7_pipeline_gate", "r7_balanced_successor_gate.py")
final = _load("r7_pipeline_final", "verify_v023_lcsrs_final.py")
preflight = _load("r7_pipeline_preflight", "preflight_r7_balanced.py")
sealer = _load("r7_pipeline_sealer", "seal_v023_lcsrs_result_directory.py")
source_stage = _load(
    "r7_pipeline_source_stage", "verify_v023_lcsrs_source_stage.py"
)


def _reports(*, raw_r6_would_pass_but_balanced_fails: bool = False):
    reports = []
    target = np.asarray([0.03] * 3 + [-0.03] * 12, dtype=np.float64)
    if raw_r6_would_pass_but_balanced_fails:
        # INFORMED wins the old raw test (0.80 versus 0.60, gap 0.20) while
        # losing the prospective balanced test (0.50 versus 0.75).
        informed = np.asarray([-0.1] * 3 + [-0.2] * 12, dtype=np.float64)
        placebo = np.asarray([0.1] * 3 + [-0.1] * 6 + [0.1] * 6, dtype=np.float64)
    else:
        # Both arms have raw accuracy 0.40.  Only the balanced rule sees the
        # INFORMED advantage: 0.625 versus 0.25.
        informed = np.asarray([0.1] * 3 + [-0.1] * 3 + [0.1] * 9, dtype=np.float64)
        placebo = np.asarray([-0.1] * 3 + [-0.1] * 6 + [0.1] * 6, dtype=np.float64)
    for world in gate.WORLDS:
        identity = [
            {
                "world": world,
                "anchor": f"w{world}:synthetic",
                "user": row,
                "action": 0,
            }
            for row in range(target.size)
        ]
        for seed in gate.STUDENT_SEEDS:
            for arm, prediction in (
                ("INFORMED", informed),
                ("MATCHED_PLACEBO", placebo),
            ):
                reports.append(
                    {
                        "held_out_world": world,
                        "student_seed": seed,
                        "arm": arm,
                        "prediction": prediction.copy(),
                        "target": target.copy(),
                        "identity": [dict(item) for item in identity],
                        "spearman": gate.tie_aware_spearman(prediction, target),
                    }
                )
    return reports


def _all_unchanged_predicates() -> dict[str, bool]:
    return {
        "integrity": True,
        "pair_coverage": True,
        "mechanics": True,
        "physical_signature": True,
        "teacher_composition": True,
        "target_support": True,
        "held_out_learner": True,
        "world_stability": True,
        "action_exposure": True,
        "literal_11": True,
        "harmful_partial": True,
        "topology_consistency": True,
        "learned_composition": True,
        "service": True,
    }


def _synthetic_final_receipt(reports) -> dict[str, object]:
    panel = final._fit_panel_metrics(reports)
    predicates = _all_unchanged_predicates()
    predicates.update(
        target_support=bool(panel["predicates"]["target_support"]),
        held_out_learner=bool(panel["predicates"]["held_out_learner"]),
        world_stability=bool(panel["predicates"]["world_stability"]),
    )
    return {
        "schema": "synthetic-r7-final-receipt-test-v1",
        "fit_panel": panel,
        "predicates": predicates,
        "c3_decision": final.adjudicate_section14(**predicates),
        "test_split_opened": False,
        "episode_training": False,
    }


def test_balanced_success_reaches_r7_go_with_zero_raw_gap() -> None:
    receipt = _synthetic_final_receipt(_reports())
    aggregate = receipt["fit_panel"]["aggregate"]
    assert receipt["c3_decision"] == "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"
    assert aggregate["informed_minus_placebo_raw_sign_accuracy"] == pytest.approx(0.0)
    assert aggregate["informed_minus_placebo_balanced_accuracy"] == pytest.approx(0.375)
    assert receipt["fit_panel"]["decision_basis"] == {
        "balanced_accuracy": "PRIMARY",
        "raw_sign_accuracy": "SERIALIZED_NONDECISIVE",
    }
    assert receipt["test_split_opened"] is False
    assert receipt["episode_training"] is False


def test_old_raw_success_cannot_rescue_failed_r7_balanced_predicate() -> None:
    receipt = _synthetic_final_receipt(
        _reports(raw_r6_would_pass_but_balanced_fails=True)
    )
    aggregate = receipt["fit_panel"]["aggregate"]
    assert aggregate["mean_informed_raw_sign_accuracy"] == pytest.approx(0.80)
    assert aggregate["informed_minus_placebo_raw_sign_accuracy"] == pytest.approx(0.20)
    assert aggregate["mean_informed_balanced_accuracy"] == pytest.approx(0.50)
    assert aggregate["informed_minus_placebo_balanced_accuracy"] == pytest.approx(-0.25)
    assert receipt["fit_panel"]["predicates"]["held_out_learner"] is False
    assert receipt["c3_decision"] == "STOP_OBSERVABILITY_R7"


@pytest.mark.parametrize("field,offset", [("held_out_world", -96), ("student_seed", -100)])
def test_old_r6_schedule_identity_is_rejected(field: str, offset: int) -> None:
    reports = _reports()
    reports[0] = dict(reports[0], **{field: int(reports[0][field]) + offset})
    with pytest.raises(
        final.V023FinalVerificationError,
        match="duplicate or out-of-panel identity",
    ):
        final._fit_panel_metrics(reports)


def test_cross_arm_heldout_identity_drift_is_rejected_before_decision() -> None:
    reports = _reports()
    reports[1] = dict(reports[1])
    reports[1]["identity"] = [dict(item) for item in reports[1]["identity"]]
    reports[1]["identity"][0]["user"] += 1
    with pytest.raises(
        final.V023FinalVerificationError,
        match="identities/labels disagree",
    ):
        final._fit_panel_metrics(reports)


def test_complete_section14_precedence_and_r7_scientific_tokens() -> None:
    base = _all_unchanged_predicates()
    cases = [
        ({key: False for key in base}, "INVALID_RUN"),
        (base | {"pair_coverage": False, "mechanics": False}, "INSUFFICIENT_PAIRS_R7"),
        (base | {"mechanics": False, "target_support": False}, "STOP_PHYSICS_R7"),
        (base | {"target_support": False, "action_exposure": False}, "STOP_OBSERVABILITY_R7"),
        (base | {"action_exposure": False}, "REDESIGN_INTERFACE_R7"),
        (base, "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7"),
    ]
    for predicates, expected in cases:
        assert final.adjudicate_section14(**predicates) == expected

    assert sealer.R7_SCIENTIFIC_TOKENS == {
        "INSUFFICIENT_PAIRS_R7",
        "STOP_PHYSICS_R7",
        "STOP_OBSERVABILITY_R7",
        "REDESIGN_INTERFACE_R7",
        "GO_FIXED_LEARNER_SCREEN_CONTRACT_R7",
    }
    assert source_stage.SCHEMA == sealer.SOURCE_STAGE_SCHEMA
    assert source_stage.classify_source_panel(
        {"predicates": {"pair_coverage": False}}
    ) == "INSUFFICIENT_PAIRS_R7"
    assert source_stage.classify_source_panel(
        {"predicates": {"pair_coverage": True}}
    ) == "SOURCE_STAGE_READY_FOR_FIT_R7"

    for field in ("physical_signature", "teacher_composition"):
        assert final.adjudicate_section14(**(base | {field: False})) == "STOP_PHYSICS_R7"
    for field in ("held_out_learner", "world_stability"):
        assert final.adjudicate_section14(**(base | {field: False})) == "STOP_OBSERVABILITY_R7"
    for field in (
        "literal_11",
        "harmful_partial",
        "topology_consistency",
        "learned_composition",
        "service",
    ):
        assert final.adjudicate_section14(**(base | {field: False})) == "REDESIGN_INTERFACE_R7"


def test_no_launch_preflight_and_blocked_operational_wrappers() -> None:
    receipt = preflight.validate_manifest()
    assert receipt["status"] == "PASS_NO_LAUNCH_PREFLIGHT"
    assert receipt["launch"] == "NO_LAUNCH"
    assert receipt["worlds"] == list(gate.WORLDS)
    assert receipt["student_seeds"] == list(gate.STUDENT_SEEDS)
    compatibility = preflight.validate_manifest(
        HERE / "PREFLIGHT-MANIFEST.json",
        manifest_digest_path=HERE / "PREFLIGHT-MANIFEST.sha256",
    )
    assert compatibility["worlds"] == list(gate.WORLDS)
    assert compatibility["student_seeds"] == list(gate.STUDENT_SEEDS)
    assert compatibility["launch"] == "NO_LAUNCH"

    for filename in (
        "r7_launch_blocker.sh",
        "sync_launch_v023_lcsrs_gate_server_r6.sh",
        "finalize_v023_lcsrs_gate_server.sh",
    ):
        completed = subprocess.run(
            ["bash", str(HERE / filename)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 2
        assert "R7_NO_LAUNCH" in completed.stderr

    launcher = (HERE / "run_v023_lcsrs_full_gate_server.sh").read_text(encoding="utf-8")
    assert launcher.index('bash "$LAUNCH_BLOCKER"') < launcher.index('mkdir -p "$RUN_ROOT"')
    assert "ssh " not in launcher.lower()
    for filename in (
        "run_v023_lcsrs_source_server.py",
        "run_v023_lcsrs_fit_server.py",
        "run_v023_lcsrs_composition_server.py",
    ):
        server = (HERE / filename).read_text(encoding="utf-8")
        parse_marker = "_parser().parse_args" if "_parser().parse_args" in server else "parser.parse_args"
        assert server.index("R7_NO_LAUNCH") < server.index(parse_marker)
        completed = subprocess.run(
            [sys.executable, str(HERE / filename)],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        assert completed.returncode == 2
        assert "R7_NO_LAUNCH" in completed.stderr


def test_runtime_sources_contain_no_copied_r6_schedule_literals() -> None:
    runtime_files = [
        path
        for suffix in ("*.py", "*.sh")
        for path in HERE.glob(suffix)
        if not path.name.startswith("test_")
    ]
    old_values = {
        *(str(2026121700 + index) for index in range(5, 13)),
        *(str(2026135100 + index) for index in range(1, 4)),
    }
    for path in runtime_files:
        text = path.read_text(encoding="utf-8")
        for old_value in old_values:
            assert old_value not in text, path.name
