from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".scratch/c3-v04/run_v05_c2_controlled_screen.py"
spec = importlib.util.spec_from_file_location("w99_v05_c2_controlled_screen", SCRIPT)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)


def test_v05_arm_mapping_is_exact_and_preserves_the_frozen_simplicity_order():
    assert runner.V05_ARMS == (
        "CT-MAIN-VALUE",
        "CT-Q13-VALUE",
        "CT-Q13-HUBER",
    )
    assert tuple(runner.V05_ARM_TO_LEARNER.values()) == (
        runner.legacy.C2_MAIN_VALUE,
        runner.legacy.C2_Q13_VALUE,
        runner.legacy.C2_Q13_HUBER,
    )
    assert runner.LEARNER_TO_V05_ARM == {
        value: key for key, value in runner.V05_ARM_TO_LEARNER.items()
    }


def test_hashed_mapping_accepts_exact_canonical_bytes_and_rejects_drift():
    body = {"schema": "fixture", "value": 7}
    value = body | {"receipt_sha256": runner.source._canonical_sha256(body)}
    assert runner._verify_hashed_mapping(
        value,
        hash_field="receipt_sha256",
        field="fixture",
    ) == value
    with pytest.raises(runner.ControlledScreenError, match="self-digest"):
        runner._verify_hashed_mapping(
            value | {"value": 8},
            hash_field="receipt_sha256",
            field="fixture",
        )


def test_gate_binding_requires_rung_100_and_exact_three_lineages():
    phase = {"merge_sha256": "a" * 64}
    selected = {str(seed): {} for seed in runner.source.Q13_SEEDS}
    runner._gate_binding(
        phase,
        {"selected_q3_rung": 100, "result": {"selected_hybrids": selected}},
    )
    with pytest.raises(runner.ControlledScreenError, match="rung 100"):
        runner._gate_binding(
            phase,
            {"selected_q3_rung": 500, "result": {"selected_hybrids": selected}},
        )
    with pytest.raises(runner.ControlledScreenError, match="three frozen lineages"):
        runner._gate_binding(
            phase,
            {
                "selected_q3_rung": 100,
                "result": {"selected_hybrids": {str(runner.source.Q13_SEEDS[0]): {}}},
            },
        )


def test_adapter_installs_only_source_prepare_gate_and_batch_seams():
    phase = {"merge_sha256": "b" * 64}
    runner._install_adapters(phase)
    assert runner.legacy.FIELD_COMPONENT == runner.V05_FIELD_COMPONENT
    assert runner.legacy.authenticate_phase_b(Path("ignored"), phase_a_dir=Path("ignored")) is phase
    assert runner.legacy.build_pair_batch is runner._build_pair_batch
    assert runner.legacy._phase_b_gate_binding is runner._gate_binding
    assert runner.legacy.authenticate_prepare is runner._authenticate_prepare


def test_mapped_result_exposes_paper_facing_v05_id_without_losing_learner_id():
    raw = {
        "candidate_id": runner.legacy.C2_Q13_HUBER,
        "selected": {
            "candidate_id": runner.legacy.C2_Q13_VALUE,
            "checkpoint_update": 100,
        },
    }
    mapped = runner._mapped_result(raw)
    assert mapped["candidate_id"] == "CT-Q13-HUBER"
    assert mapped["learner_candidate_id"] == runner.legacy.C2_Q13_HUBER
    assert mapped["selected"]["candidate_id"] == "CT-Q13-VALUE"
    assert mapped["selected"]["learner_candidate_id"] == runner.legacy.C2_Q13_VALUE
    assert mapped["adapter_schema"] == runner.V05_ADAPTER_SCHEMA
