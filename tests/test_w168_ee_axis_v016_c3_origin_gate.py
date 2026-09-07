"""W-168 -- pure V0.16-O source-only gate mechanics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


REPO = Path(__file__).resolve().parents[1]
RUNNER = (
    REPO
    / ".scratch"
    / "multi-catfish-v016-c3-origin-gate"
    / "run_v016_origin_gate.py"
)
SPEC = importlib.util.spec_from_file_location("mcrl_v016_origin_gate_w168", RUNNER)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)


SOURCE_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v016_origin_source_w168",
    RUNNER.with_name("run_v016_origin_source_shard.py"),
)
assert SOURCE_SPEC is not None and SOURCE_SPEC.loader is not None
source_runner = importlib.util.module_from_spec(SOURCE_SPEC)
sys.modules[SOURCE_SPEC.name] = source_runner
SOURCE_SPEC.loader.exec_module(source_runner)


def _readonly(value, dtype):
    result = np.array(value, dtype=dtype, copy=True)
    result.setflags(write=False)
    return result


def _rows(groups: int = 2):
    contexts = np.tile(np.asarray([12, 1, 2], dtype=np.int64), groups)
    rows = contexts.size
    masks = np.zeros((rows, 28), dtype=np.bool_)
    masks[:, :3] = True
    q1 = np.zeros((rows, 28), dtype=np.float64)
    q2 = np.zeros((rows, 28), dtype=np.float64)
    q1[:, 0] = 2.0
    q1[:, 1] = 1.0
    q2[:, 1] = 2.0
    q2[:, 2] = 1.0
    references = np.asarray(
        [1 if code == 12 else 0 if code == 1 else 1 for code in contexts],
        dtype=np.int64,
    )
    z3 = np.zeros((rows, 28), dtype=np.float64)
    compatibility = masks.copy()
    states = np.zeros((rows, 402), dtype=np.float32)
    for group in range(groups):
        # Reference-conditioned V0.15 blocks, the physical-origin indicator,
        # and the three appended origin summaries may all differ by context.
        # The native prefix and the seven inherited globals remain fixed.
        states[3 * group : 3 * group + 3, 280:364] = np.asarray(
            [[0.1], [0.2], [0.3]], dtype=np.float32
        )
        for offset, reference in enumerate(references[3 * group : 3 * group + 3]):
            states[3 * group + offset, 364 + int(reference)] = 1.0
        states[3 * group : 3 * group + 3, 399:402] = np.asarray(
            [[0.0], [0.2], [0.3]], dtype=np.float32
        )
        if group > 0:
            states[3 * group, 399] = np.float32(0.5)
    worlds = np.repeat(np.arange(100, 100 + groups, dtype=np.int64), 3)
    lineages = np.full(rows, 7, dtype=np.int64)
    anchors = np.asarray(
        [f"{'a' if group == 0 else 'b'}" * 64 for group in range(groups) for _ in range(3)],
        dtype="S64",
    )
    steps = np.repeat(np.arange(groups, dtype=np.int64), 3)
    users = np.zeros(rows, dtype=np.int64)
    return gate.ReferenceRows(
        q3_states=_readonly(states, np.float32),
        action_masks=_readonly(masks, np.bool_),
        q1_values=_readonly(q1, np.float64),
        learned_q2_values=_readonly(q2, np.float64),
        z3_target_bits=_readonly(z3, np.float64),
        q3_compatibility=_readonly(compatibility, np.bool_),
        context_codes=_readonly(contexts, np.int64),
        reference_actions=_readonly(references, np.int64),
        source_seeds=_readonly(worlds, np.int64),
        lineages=_readonly(lineages, np.int64),
        anchor_sha256s=_readonly(anchors, np.dtype("S64")),
        step_indices=_readonly(steps, np.int64),
        user_indices=_readonly(users, np.int64),
    )


def test_source_closure_enforces_three_contexts_and_hidden_ablation_boundary() -> None:
    rows = _rows()
    rows.verify()
    assert rows.context(12).rows == 2
    assert rows.context(1).rows == 2
    assert rows.context(2).rows == 2

    bad_references = np.array(rows.reference_actions, copy=True)
    bad_references[1] = 1  # h=1 must use Q1-only action 0.
    bad_references.setflags(write=False)
    bad = gate.ReferenceRows(
        **{
            **rows.__dict__,
            "reference_actions": bad_references,
        }
    )
    with pytest.raises(gate.V016OriginGateError, match="masked base-head argmax"):
        bad.verify()

    bad_states = np.array(rows.q3_states, copy=True)
    bad_states[1, gate.V016_C3_GLOBAL_START] = 1.0
    bad_states.setflags(write=False)
    with pytest.raises(gate.V016OriginGateError, match="native state"):
        gate.ReferenceRows(**{**rows.__dict__, "q3_states": bad_states}).verify()


def test_origin_zero_change_diagnostic_is_report_only_and_measured() -> None:
    rows = _rows()
    learner = gate.EEAxisV015C3PivotalLearner(
        gate._q3_config(), train_seed=17
    )
    report = gate.evaluate_context(learner, rows, 12)
    assert report["origin_peer_zero_rows"] == 1
    assert report["student_change_count_when_origin_peer_zero"] == 0
    assert report["student_change_rate_when_origin_peer_zero"] == 0.0
    assert "origin_peer_zero" not in gate.adjudicate_rung_3000(
        {
            12: _report(
                background=0.70,
                learned=0.80,
                pivotal=0.50,
                stable=0.95,
                changes=3,
                support=0.80,
            ),
            1: _report(
                background=0.80,
                learned=0.80,
                pivotal=0.0,
                stable=1.0,
                changes=0,
                support=None,
            ),
            2: _report(
                background=0.75,
                learned=0.76,
                pivotal=0.0,
                stable=1.0,
                changes=0,
                support=None,
            ),
        }
    )["clauses"]


def test_balanced_batch_has_equal_context_contributions() -> None:
    rows = _rows(groups=3)
    pairs = {code: gate._pairs_for_context(rows, code) for code in gate.CONTEXT_CODES}
    batch = gate._take_balanced(pairs, update=1, per_context=4)
    assert batch.rows == 12
    # Context order is frozen as h=12, h=1, h=2.  The stored base/reference
    # action exposes the exact four-row contribution from each context.
    assert batch.reference_actions[:4].tolist() == [1, 1, 1, 1]
    assert batch.reference_actions[4:8].tolist() == [0, 0, 0, 0]
    assert batch.reference_actions[8:].tolist() == [1, 1, 1, 1]


def _report(*, background, learned, pivotal, stable, changes, support):
    return {
        "background_teacher_agreement": background,
        "learned_teacher_agreement": learned,
        "pivotal_agreement": pivotal,
        "stable_preservation": stable,
        "student_change_count": changes,
        "positive_compatible_support_fraction": support,
    }


def test_mechanical_decision_requires_every_frozen_clause() -> None:
    reports = {
        12: _report(
            background=0.70,
            learned=0.80,
            pivotal=0.50,
            stable=0.95,
            changes=3,
            support=0.80,
        ),
        1: _report(
            background=0.80,
            learned=0.80,
            pivotal=0.0,
            stable=1.0,
            changes=0,
            support=None,
        ),
        2: _report(
            background=0.75,
            learned=0.76,
            pivotal=0.0,
            stable=1.0,
            changes=0,
            support=None,
        ),
    }
    assert gate.adjudicate_rung_3000(reports)["passed"] is True
    reports[2]["learned_teacher_agreement"] = 0.74
    decision = gate.adjudicate_rung_3000(reports)
    assert decision["passed"] is False
    assert decision["clauses"]["h2_teacher_agreement_noninferior"] is False


def test_contract_and_network_layout_are_frozen_consistently() -> None:
    assert gate.validate_frozen_contract() == gate.CONTRACT_SHA256
    config = gate._q3_config()
    assert config.local_feature_dim == 14
    assert config.global_feature_dim == 10
    assert config.state_dim == 402


def test_b402_only_changes_the_state_carrier_and_keeps_v015_learner_path() -> None:
    """The V0.16 gate must retain the V0.15 pivotal target/loss seam."""

    assert gate.EEAxisV015C3PivotalLearner.__module__ == (
        "mcrl.runtime.ee_axis_v015_c3_pivotal"
    )
    assert gate.V015C3PivotalPairs.__module__ == (
        "mcrl.runtime.ee_axis_v015_c3_pivotal"
    )
    runner_text = RUNNER.read_text(encoding="utf-8")
    assert "build_pivotal_pairs" in runner_text
    assert "EEAxisV015C3PivotalLearner" in runner_text
    assert "V015C3PivotalPairs" in runner_text
    assert "target_surplus_bits" in runner_text
    assert "learning_rate=0.001" in runner_text
    assert "beta=0.1" in runner_text
    assert "hidden_layers=(100, 50, 50)" in runner_text
    contract = gate.CONTRACT_PATH.read_text(encoding="utf-8")
    assert "Retain the existing V0.15 pivotal residual source and loss without alteration" in contract
    assert "any C1, C2, canonical-EE, Q1, or frozen-Q2 change" in contract


def test_gate_loader_authenticates_source_runner_roundtrip(tmp_path: Path) -> None:
    users = source_runner.USERS
    contexts = np.concatenate(
        [np.full(users, code, dtype=np.int64) for code in gate.CONTEXT_CODES]
    )
    rows = contexts.size
    masks = np.zeros((rows, 28), dtype=np.bool_)
    masks[:, :3] = True
    q1 = np.zeros((rows, 28), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0] = 2.0
    q1[:, 1] = 1.0
    q2[:, 1] = 2.0
    q2[:, 2] = 1.0
    references = np.where(contexts == 1, 0, 1).astype(np.int64)
    world = gate.TRAIN_WORLD_SEEDS[0]
    lineage = gate.SOURCE_LINEAGES[0]
    source = source_runner.assemble_source_arrays(
        q3_states=np.zeros((rows, 402), dtype=np.float32),
        action_masks=masks,
        q1_values=q1,
        learned_q2_values=q2,
        z3_target_bits=np.zeros((rows, 28), dtype=np.float64),
        q3_compatibility=masks,
        context_codes=contexts,
        reference_actions=references,
        source_seeds=np.full(rows, world, dtype=np.int64),
        lineages=np.full(rows, lineage, dtype=np.int64),
        anchor_sha256s=np.full(rows, b"a" * 64, dtype="S64"),
        step_indices=np.zeros(rows, dtype=np.int64),
        user_indices=np.tile(np.arange(users, dtype=np.int64), 3),
        world_seed=world,
        lineage=lineage,
        field_root_digest="f" * 64,
        kappa_bits=source_runner.OPS3_KAPPA_BITS,
        q1_checkpoint_sha256="1" * 64,
        q2_checkpoint_sha256=gate.Q2_CHECKPOINT_SHA256_BY_LINEAGE[lineage],
        q1_parameter_sha256="3" * 64,
        q2_parameter_sha256="4" * 64,
    )
    shard = tmp_path / "shard"
    source_runner.write_source_shard(
        shard,
        source,
        metadata_extra={
            "source_runner_sha256": gate._file_sha256(
                gate.SOURCE_RUNNER_PATH
            ),
        },
    )
    loaded = gate.load_reference_rows((shard,), lineage=lineage, worlds=(world,))
    assert loaded.rows == rows
    assert loaded.context(12).rows == users
    assert loaded.context(1).rows == users
    assert loaded.context(2).rows == users
