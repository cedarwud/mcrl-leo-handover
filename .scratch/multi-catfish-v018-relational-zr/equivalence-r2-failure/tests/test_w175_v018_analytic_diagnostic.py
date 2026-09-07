"""Focused pure checks for the V0.18 analytic diagnostic runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v018-relational-zr"
    / "run_v018_analytic_diagnostic.py"
)
_SPEC = importlib.util.spec_from_file_location("test_v018_diagnostic_runner", RUNNER_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import failure
    raise RuntimeError(f"cannot import V0.18 runner: {RUNNER_PATH}")
runner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(runner)


def _surfaces(users: int = 3) -> tuple[np.ndarray, ...]:
    shape = (users, runner.NUM_ACTIONS)
    q1 = np.zeros(shape, dtype=np.float64)
    q2 = np.zeros(shape, dtype=np.float64)
    exact = np.zeros(shape, dtype=np.float64)
    nominal = np.zeros(shape, dtype=np.float64)
    exact[0, 2] = 10.0
    nominal[0, 1] = 5.0
    masks = np.ones(shape, dtype=np.bool_)
    return q1, q2, exact, nominal, masks


def test_score_composition_and_arm_labels_are_native_masked() -> None:
    q1, q2, exact, nominal, masks = _surfaces()
    assert runner.ARMS == ("BASE", "EXACT_ZR", "NOMINAL_ZR")

    _, base_actions = runner.compose_arm_scores(q1, q2, exact, nominal, masks, "BASE")
    _, exact_actions = runner.compose_arm_scores(q1, q2, exact, nominal, masks, "EXACT_ZR")
    _, nominal_actions = runner.compose_arm_scores(q1, q2, exact, nominal, masks, "NOMINAL_ZR")

    assert int(base_actions[0]) == 0
    assert int(exact_actions[0]) == 2
    assert int(nominal_actions[0]) == 1
    assert np.all(base_actions == 0)


def test_nominal_arm_cannot_accidentally_read_exact_surface() -> None:
    q1, q2, exact, nominal, masks = _surfaces()
    score_a, action_a = runner.compose_arm_scores(
        q1, q2, exact, nominal, masks, "NOMINAL_ZR"
    )
    exact_changed = exact * 1000.0
    score_b, action_b = runner.compose_arm_scores(
        q1, q2, exact_changed, nominal, masks, "NOMINAL_ZR"
    )
    np.testing.assert_array_equal(action_a, action_b)
    np.testing.assert_array_equal(score_a, score_b)


def test_source_context_metrics_require_pivotal_and_supported_nominal_change() -> None:
    q1, q2, exact, nominal, masks = _surfaces()
    nominal = nominal.copy()
    nominal[0, 1] = 0.0
    nominal[0, 2] = 5.0
    report = runner._source_context_metrics(
        context=12,
        base_surface=q1 + q2,
        exact_q3=exact,
        nominal_q3=nominal,
        masks=masks,
        compatible=np.ones_like(masks, dtype=np.bool_),
    )
    assert report["nominal_teacher_agreement"] > report["base_teacher_agreement"]
    assert report["pivotal_agreement"] >= 0.50
    assert report["stable_preservation"] >= 0.95
    assert report["nominal_change_count"] == 1
    assert report["nominal_change_positive_compatible_fraction"] == 1.0
    assert report["passed"] is True


def test_source_context_summary_adds_counts_instead_of_using_last_report() -> None:
    q1, q2, exact, nominal, masks = _surfaces()
    nominal = nominal.copy()
    nominal[0, 1] = 0.0
    nominal[0, 2] = 5.0
    good = runner._source_context_metrics(
        context=12,
        base_surface=q1 + q2,
        exact_q3=exact,
        nominal_q3=nominal,
        masks=masks,
        compatible=np.ones_like(masks, dtype=np.bool_),
    )
    bad = dict(good)
    bad["agreement_count"] = 0
    bad["nominal_teacher_agreement"] = 0.0
    bad["passed"] = False
    summary = runner._source_context_summary([good, bad])
    pooled = summary["contexts"]["12"]
    assert pooled["report_count"] == 2
    assert pooled["row_count"] == 2 * masks.shape[0]
    assert pooled["nominal_teacher_agreement"] < good["nominal_teacher_agreement"]
    assert summary["passed"] is False


def test_panel_source_summary_uses_base_rows_and_pools_each_lineage() -> None:
    q1, q2, exact, nominal, masks = _surfaces()
    nominal = nominal.copy()
    nominal[0, 1] = 0.0
    nominal[0, 2] = 5.0
    contexts = {}
    for context in (12, 1, 2):
        contexts[str(context)] = runner._source_context_metrics(
            context=context,
            base_surface=q1 + q2,
            exact_q3=exact,
            nominal_q3=nominal,
            masks=masks,
            compatible=np.ones_like(masks, dtype=np.bool_),
        )
    rows = [_gate_row("BASE", bits=100.0)]
    rows[0]["source_diagnostics"] = {"contexts": contexts, "passed": True}
    rows.extend(
        [
            dict(_gate_row("EXACT_ZR", bits=110.0), source_diagnostics={"passed": False}),
            dict(_gate_row("NOMINAL_ZR", bits=105.0), source_diagnostics={"passed": False}),
        ]
    )
    panel = runner._source_diagnostics_panel_summary(rows)
    assert panel["passed"] is True
    assert panel["by_lineage"]["2"]["passed"] is True


def _gate_row(arm: str, *, bits: float) -> dict[str, object]:
    return {
        "world_seed": 1,
        "lineage": 2,
        "arm": arm,
        "initial_world_sha256": "world",
        "field_root_digest": "field",
        "q1_checkpoint_sha256": "q1",
        "q2_checkpoint_sha256": "q2",
        "total_bits": bits,
        "total_energy_j": 10.0,
        "served_user_steps": 10,
        "served_opportunities": 10,
        "mechanics_passed": True,
        "compatibility_proof_passed": True,
        "source_diagnostics_passed": True,
    }


def test_panel_identity_enforces_same_world_field_and_checkpoints() -> None:
    rows = [_gate_row("BASE", bits=100.0), _gate_row("EXACT_ZR", bits=110.0), _gate_row("NOMINAL_ZR", bits=105.0)]
    indexed = runner._validate_panel_identity(rows, worlds=(1,), lineages=(2,))
    assert set(indexed) == {(1, "BASE", 2), (1, "EXACT_ZR", 2), (1, "NOMINAL_ZR", 2)}

    broken = [dict(row) for row in rows]
    broken[1]["field_root_digest"] = "different"
    with pytest.raises(runner.V018OracleError):
        runner._validate_panel_identity(broken, worlds=(1,), lineages=(2,))


def test_panel_rows_are_compatible_with_pure_v018_gate() -> None:
    rows = [_gate_row("BASE", bits=100.0), _gate_row("EXACT_ZR", bits=110.0), _gate_row("NOMINAL_ZR", bits=105.0)]
    gate = runner.adjudicate_v018_analytic_gate(
        rows,
        worlds=(1,),
        lineages=(2,),
        compatibility_proof_passed=True,
        source_diagnostics_passed=True,
    )
    assert gate["decision"] == "PASS_ANALYTIC_DIAGNOSTIC"
    assert gate["passed"] is True


def test_contract_refuses_an_undeclared_world_or_lineage() -> None:
    with pytest.raises(runner.V018OracleError, match="world"):
        runner.contract_receipt(worlds=(999999,), lineages=(runner.LINEAGES[0],))
    with pytest.raises(runner.V018OracleError, match="lineage"):
        runner.contract_receipt(
            worlds=(runner.WORLD_SEEDS[0],), lineages=(999999,)
        )


def test_frozen_contract_bytes_are_bound_not_just_its_status_text(tmp_path: Path) -> None:
    runner.validate_v018_contract()
    changed = tmp_path / runner.V018_CONTRACT_PATH.name
    changed.write_text(
        runner.V018_CONTRACT_PATH.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )
    with pytest.raises(runner.V018OracleError, match="hash"):
        runner.validate_v018_contract(changed)
