"""W-172 -- V0.17 B402 masked soft-KL source-only gate mechanics."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pytest
import torch


REPO = Path(__file__).resolve().parents[1]
RUNNER_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v017-c3-softkl-gate"
    / "run_v017_softkl_gate.py"
)
SPEC = importlib.util.spec_from_file_location(
    "mcrl_v017_softkl_gate_w172", RUNNER_PATH
)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate
SPEC.loader.exec_module(gate)

SOURCE_PATH = RUNNER_PATH.with_name("run_v017_softkl_source_shard.py")
SOURCE_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v017_softkl_source_w172", SOURCE_PATH
)
assert SOURCE_SPEC is not None and SOURCE_SPEC.loader is not None
source_runner = importlib.util.module_from_spec(SOURCE_SPEC)
sys.modules[SOURCE_SPEC.name] = source_runner
SOURCE_SPEC.loader.exec_module(source_runner)

OLD_GATE_PATH = (
    REPO
    / ".scratch"
    / "multi-catfish-v016-c3-origin-gate"
    / "run_v016_origin_gate.py"
)
OLD_SPEC = importlib.util.spec_from_file_location(
    "mcrl_v016_origin_gate_for_w172", OLD_GATE_PATH
)
assert OLD_SPEC is not None and OLD_SPEC.loader is not None
old_gate = importlib.util.module_from_spec(OLD_SPEC)
sys.modules[OLD_SPEC.name] = old_gate
OLD_SPEC.loader.exec_module(old_gate)


def _readonly(value: object, dtype: np.dtype[Any]) -> np.ndarray:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    result.setflags(write=False)
    return result


def _rows(*, anchors: int = 2, users: int = 4) -> gate.ReferenceRows:
    """Construct physical rows with exact 12/1/2 context closure.

    The first user has a one-action native mask.  Users one and two share an
    identical B402 state/mask in h=12 but have different ZR targets, making
    the alias report observable without making it a decision clause.
    """

    states: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    q1_values: list[np.ndarray] = []
    q2_values: list[np.ndarray] = []
    z3_values: list[np.ndarray] = []
    compatibility: list[np.ndarray] = []
    contexts: list[int] = []
    references: list[int] = []
    source_seeds: list[int] = []
    lineages: list[int] = []
    anchors_sha: list[bytes] = []
    step_indices: list[int] = []
    user_indices: list[int] = []

    for anchor in range(anchors):
        world = gate.TRAIN_WORLD_SEEDS[anchor % len(gate.TRAIN_WORLD_SEEDS)]
        anchor_digest = (chr(ord("a") + anchor) * 64).encode("ascii")
        for user in range(users):
            native_mask = np.zeros(gate.ACTION_DIM, dtype=np.bool_)
            native_mask[:3] = True
            if user == 0:
                native_mask[:] = False
                native_mask[1] = True
            q1 = np.zeros(gate.ACTION_DIM, dtype=np.float64)
            q2 = np.zeros_like(q1)
            q1[0], q1[1] = 2.0, 1.0
            q2[1], q2[2] = 2.0, 1.0
            reference_by_context = {12: 1, 1: 0, 2: 1}
            if user == 0:
                reference_by_context = {12: 1, 1: 1, 2: 1}

            for code in gate.CONTEXT_CODES:
                reference = reference_by_context[code]
                state = np.zeros(gate.V016_C3_ORIGIN_STATE_DIM, dtype=np.float32)
                # The inherited V0.15 carrier is context-independent.  Only
                # the appended origin tail is allowed to differ by context.
                state[
                    gate.V016_C3_GLOBAL_START : gate.V016_C3_V015_GLOBAL_END
                ] = np.asarray(
                    [0.01 * index for index in range(7)], dtype=np.float32
                )
                state[gate.V016_C3_REFERENCE_BEAM_GLOBAL_START] = {
                    12: 0.0,
                    1: 0.25,
                    2: 0.5,
                }[code]
                state[gate.V016_C3_REFERENCE_BEAM_GLOBAL_START + 1] = 0.1
                state[gate.V016_C3_REFERENCE_BEAM_GLOBAL_START + 2] = 0.2

                z3 = np.zeros(gate.ACTION_DIM, dtype=np.float64)
                if code == 12 and user == 1:
                    # At h=12, action two then becomes the teacher action;
                    # user two remains on action one.  The reference target is
                    # still exactly zero in both rows.
                    z3[2] = 3.0 * float(gate.OPS3_KAPPA_BITS)

                states.append(state)
                masks.append(native_mask.copy())
                q1_values.append(q1.copy())
                q2_values.append(q2.copy())
                z3_values.append(z3)
                compatibility.append(native_mask.copy())
                contexts.append(code)
                references.append(reference)
                source_seeds.append(world)
                lineages.append(gate.SOURCE_LINEAGES[anchor % len(gate.SOURCE_LINEAGES)])
                anchors_sha.append(anchor_digest)
                step_indices.append(anchor)
                user_indices.append(user)

    return gate.ReferenceRows(
        q3_states=_readonly(states, np.dtype(np.float32)),
        action_masks=_readonly(masks, np.dtype(np.bool_)),
        q1_values=_readonly(q1_values, np.dtype(np.float64)),
        learned_q2_values=_readonly(q2_values, np.dtype(np.float64)),
        z3_target_bits=_readonly(z3_values, np.dtype(np.float64)),
        q3_compatibility=_readonly(compatibility, np.dtype(np.bool_)),
        context_codes=_readonly(contexts, np.dtype(np.int64)),
        reference_actions=_readonly(references, np.dtype(np.int64)),
        source_seeds=_readonly(source_seeds, np.dtype(np.int64)),
        lineages=_readonly(lineages, np.dtype(np.int64)),
        anchor_sha256s=_readonly(anchors_sha, np.dtype("S64")),
        step_indices=_readonly(step_indices, np.dtype(np.int64)),
        user_indices=_readonly(user_indices, np.dtype(np.int64)),
    )


def _source_arrays(
    *,
    world: int,
    lineage: int,
    anchors: int = 1,
    q2_digest: str | None = None,
) -> dict[str, object]:
    rows_per_anchor = source_runner.USERS * len(source_runner.CONTEXT_CODES)
    rows = anchors * rows_per_anchor
    context_group = np.concatenate(
        [
            np.full(source_runner.USERS, code, dtype=np.int64)
            for code in source_runner.CONTEXT_CODES
        ]
    )
    contexts = np.tile(context_group, anchors)
    users = np.tile(
        np.tile(np.arange(source_runner.USERS, dtype=np.int64), 3), anchors
    )
    steps = np.repeat(np.arange(anchors, dtype=np.int64), rows_per_anchor)
    anchor_sha = np.repeat(
        np.asarray(
            [chr(ord("a") + index) * 64 for index in range(anchors)],
            dtype="S64",
        ),
        rows_per_anchor,
    )
    masks = np.zeros((rows, source_runner.ACTION_DIM), dtype=np.bool_)
    masks[:, :3] = True
    for anchor in range(anchors):
        for context_offset in range(len(source_runner.CONTEXT_CODES)):
            row = anchor * rows_per_anchor + context_offset * source_runner.USERS
            masks[row] = False
            masks[row, 1] = True
    q1 = np.zeros((rows, source_runner.ACTION_DIM), dtype=np.float64)
    q2 = np.zeros_like(q1)
    q1[:, 0], q1[:, 1] = 2.0, 1.0
    q2[:, 1], q2[:, 2] = 2.0, 1.0
    refs = np.empty(rows, dtype=np.int64)
    for index, code in enumerate(contexts.tolist()):
        refs[index] = 1 if np.count_nonzero(masks[index]) == 1 or code != 1 else 0
    return {
        "q3_states": np.zeros(
            (rows, source_runner.V016_C3_ORIGIN_STATE_DIM), dtype=np.float32
        ),
        "action_masks": masks,
        "q1_values": q1,
        "learned_q2_values": q2,
        "z3_target_bits": np.zeros_like(q1),
        "q3_compatibility": masks.copy(),
        "context_codes": contexts,
        "reference_actions": refs,
        "source_seeds": np.full(rows, int(world), dtype=np.int64),
        "lineages": np.full(rows, int(lineage), dtype=np.int64),
        "anchor_sha256s": anchor_sha,
        "step_indices": steps,
        "user_indices": users,
        "world_seed": int(world),
        "lineage": int(lineage),
        "field_root_digest": "f" * 64,
        "kappa_bits": float(source_runner.OPS3_KAPPA_BITS),
        "q1_checkpoint_sha256": "1" * 64,
        "q2_checkpoint_sha256": q2_digest
        or gate.Q2_CHECKPOINT_SHA256_BY_LINEAGE[int(lineage)],
        "q1_parameter_sha256": "3" * 64,
        "q2_parameter_sha256": "4" * 64,
    }


def _source(
    *,
    world: int,
    lineage: int,
    q2_digest: str | None = None,
):
    return source_runner.assemble_source_arrays(
        **_source_arrays(world=world, lineage=lineage, q2_digest=q2_digest)
    )


def _write_source(
    output: Path,
    *,
    world: int,
    lineage: int,
    source_runner_digest: str | None = None,
    q2_digest: str | None = None,
) -> Path:
    source = _source(world=world, lineage=lineage, q2_digest=q2_digest)
    q2_value = q2_digest or gate.Q2_CHECKPOINT_SHA256_BY_LINEAGE[lineage]
    source_runner.write_source_shard(
        output,
        source,
        metadata_extra={
            "source_runner_sha256": source_runner_digest
            or gate._file_sha256(gate.SOURCE_RUNNER_PATH),
            "q1_checkpoint": {
                "checkpoint_sha256": "1" * 64,
                "parameter_sha256": "3" * 64,
            },
            "q2_checkpoint": {
                "checkpoint_sha256": q2_value,
                "parameter_sha256": "4" * 64,
            },
        },
    )
    return output


def _report(
    *,
    background: float,
    learned: float,
    pivotal: float | None,
    stable: float | None,
    changes: int,
    support: float | None,
) -> dict[str, object]:
    return {
        "background_teacher_agreement": background,
        "learned_teacher_agreement": learned,
        "pivotal_agreement": pivotal,
        "stable_preservation": stable,
        "student_change_count": changes,
        "positive_compatible_support_fraction": support,
    }


def _passing_reports() -> dict[int, dict[str, object]]:
    return {
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
            pivotal=None,
            stable=1.0,
            changes=0,
            support=None,
        ),
        2: _report(
            background=0.75,
            learned=0.76,
            pivotal=None,
            stable=1.0,
            changes=0,
            support=None,
        ),
    }


def test_v017_gate_declares_new_schemas_seeds_and_disjoint_splits() -> None:
    assert gate.RUNNER_SCHEMA == "multi-catfish-mcrl-v017-c3-softkl-learnability-gate-v1"
    assert gate.RESULT_SCHEMA == "multi-catfish-mcrl-v017-c3-softkl-learnability-result-v1"
    assert gate.CHECKPOINT_SCHEMA == "multi-catfish-mcrl-v017-c3-softkl-learnability-checkpoint-v1"
    assert gate.CLAIM_CEILING == (
        "TRAIN_VALIDATION_SOURCE_ONLY_NO_TRAJECTORY_EE_OR_EFFICACY_CLAIM"
    )
    assert tuple(gate.TRAIN_WORLD_SEEDS) == (2026112001, 2026112002, 2026112003)
    assert tuple(gate.VALIDATION_WORLD_SEEDS) == (2026112004, 2026112005, 2026112006)
    assert set(gate.TRAIN_WORLD_SEEDS).isdisjoint(gate.VALIDATION_WORLD_SEEDS)
    assert tuple(gate.SOURCE_LINEAGES) == tuple(source_runner.LINEAGES)
    assert tuple(gate.INITIALIZATION_SEEDS) == (2026112101, 2026112102, 2026112103)
    assert gate.UPDATE_RUNGS == (3, 10, 30, 100, 300, 1000, 3000)
    assert gate.validate_frozen_contract() == gate.CONTRACT_SHA256


def test_reference_rows_close_contexts_and_materialize_context_specific_B() -> None:
    rows = _rows()
    rows.verify()
    assert rows.rows == 2 * 4 * 3
    assert {code: rows.context(code).rows for code in gate.CONTEXT_CODES} == {
        12: 8,
        1: 8,
        2: 8,
    }

    batches = {
        code: gate._batch_for_context(rows, code) for code in gate.CONTEXT_CODES
    }
    expected = {
        12: rows.context(12).q1_values + rows.context(12).learned_q2_values,
        1: rows.context(1).q1_values,
        2: rows.context(2).learned_q2_values,
    }
    for code, batch in batches.items():
        assert batch.schema == "multi-catfish-mcrl-b402-c3-softkl-batch-v1"
        np.testing.assert_allclose(batch.background_values, expected[code])
        assert batch.rows == rows.context(code).rows
        assert int(np.count_nonzero(np.sum(batch.action_masks, axis=1) == 1)) == 2
        assert np.all(
            batch.action_masks[
                np.arange(batch.rows), batch.reference_actions
            ]
        )


def test_balanced_training_batch_uses_every_full_row_and_keeps_one_action_rows() -> None:
    rows = _rows(anchors=1, users=4)
    batches = {
        code: gate._batch_for_context(rows, code) for code in gate.CONTEXT_CODES
    }
    per_context = rows.context(12).rows
    merged = gate._take_balanced(
        batches,
        update=1,
        per_context=per_context,
    )
    assert merged.rows == per_context * len(gate.CONTEXT_CODES)
    assert int(np.count_nonzero(np.sum(merged.action_masks, axis=1) == 1)) == 3
    for offset, code in enumerate(gate.CONTEXT_CODES):
        start = offset * per_context
        end = start + per_context
        np.testing.assert_array_equal(
            merged.action_masks[start:end], batches[code].action_masks
        )
        np.testing.assert_allclose(
            merged.background_values[start:end], batches[code].background_values
        )
        np.testing.assert_array_equal(
            merged.reference_actions[start:end], batches[code].reference_actions
        )

    learner = gate.EEAxisB402SoftKLLearner(
        gate._q3_config(), train_seed=2026112101, device="cpu"
    )
    measured = learner.measure(merged)
    assert measured["batch_size"] == merged.rows
    assert np.isfinite(float(measured["loss"]))


def test_alias_diagnostics_are_report_only_and_do_not_change_the_gate() -> None:
    rows = _rows()
    diagnostics = gate.state_alias_diagnostics(rows)
    assert diagnostics["rows"] == rows.rows
    assert diagnostics["duplicate_rows"] > 0
    assert diagnostics["duplicate_groups"] > 0
    assert diagnostics["target_conflicting_groups"] > 0
    assert diagnostics["teacher_action_conflicting_groups"] > 0
    assert diagnostics["max_abs_target_conflict_bits"] > 0.0
    assert diagnostics["decision_clause"] is False
    decision = gate.adjudicate_rung_3000(_passing_reports())
    assert decision["passed"] is True
    assert not any("alias" in key for key in decision["clauses"])


def test_adjudication_is_exactly_unchanged_from_v016() -> None:
    reports = _passing_reports()
    assert gate.adjudicate_rung_3000(reports) == old_gate.adjudicate_rung_3000(
        reports
    )
    failed = {code: dict(report) for code, report in reports.items()}
    failed[2]["learned_teacher_agreement"] = 0.74
    assert gate.adjudicate_rung_3000(failed) == old_gate.adjudicate_rung_3000(
        failed
    )
    assert gate.adjudicate_rung_3000(failed)["clauses"][
        "h2_teacher_agreement_noninferior"
    ] is False
    with pytest.raises(gate.V017SoftKLGateError, match="all three contexts"):
        gate.adjudicate_rung_3000({12: reports[12], 1: reports[1]})


def test_gate_owns_the_new_softkl_module_and_not_the_retired_pair_learner() -> None:
    assert gate.EEAxisB402SoftKLLearner.__module__ == (
        "mcrl.runtime.ee_axis_b402_c3_softkl"
    )
    assert gate.build_b402_softkl_batch.__module__ == (
        "mcrl.runtime.ee_axis_b402_c3_softkl"
    )
    runner_text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "EEAxisB402SoftKLLearner" in runner_text
    assert "build_b402_softkl_batch" in runner_text
    assert "_batch_for_context" in runner_text
    assert "EEAxisV015C3PivotalLearner" not in runner_text
    assert "V015C3PivotalPairs" not in runner_text
    assert "build_pivotal_pairs" not in runner_text
    assert "target_surplus_bits" not in runner_text
    contract = gate.CONTRACT_PATH.read_text(encoding="utf-8")
    assert "New masked soft-KL objective" in contract
    assert "including one-action rows" in contract
    assert "replace only the" in contract
    assert "pair/hinge objective by" in contract


def test_gate_loader_authenticates_new_source_runner_and_q2_lineage(
    tmp_path: Path,
) -> None:
    world = gate.TRAIN_WORLD_SEEDS[0]
    lineage = gate.SOURCE_LINEAGES[0]
    shard = _write_source(tmp_path / "valid", world=world, lineage=lineage)
    loaded = gate.load_reference_rows((shard,), lineage=lineage, worlds=(world,))
    loaded.verify()
    assert loaded.rows == source_runner.USERS * len(source_runner.CONTEXT_CODES)
    assert {code: loaded.context(code).rows for code in gate.CONTEXT_CODES} == {
        12: source_runner.USERS,
        1: source_runner.USERS,
        2: source_runner.USERS,
    }
    assert loaded.shard_receipts[0]["source_runner_sha256"] == gate._file_sha256(
        gate.SOURCE_RUNNER_PATH
    )
    assert loaded.shard_receipts[0]["contract_sha256"] == gate.CONTRACT_SHA256

    bad_runner = _write_source(
        tmp_path / "wrong-runner",
        world=world,
        lineage=lineage,
        source_runner_digest="0" * 64,
    )
    with pytest.raises(gate.V017SoftKLGateError, match="source code or contract"):
        gate.load_reference_rows((bad_runner,), lineage=lineage, worlds=(world,))

    bad_q2 = _write_source(
        tmp_path / "wrong-q2",
        world=world,
        lineage=lineage,
        q2_digest="0" * 64,
    )
    with pytest.raises(gate.V017SoftKLGateError, match="Q2 checkpoint"):
        gate.load_reference_rows((bad_q2,), lineage=lineage, worlds=(world,))


def test_train_one_checkpoint_carries_source_only_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = _rows(anchors=1, users=2)
    monkeypatch.setattr(gate, "UPDATE_RUNGS", (1,))
    monkeypatch.setattr(gate, "BATCH_PER_CONTEXT", 2)
    original_take = gate._take_balanced

    def small_take(
        batches: dict[int, object], *, update: int, per_context: int = 2
    ):
        del per_context
        return original_take(batches, update=update, per_context=2)

    monkeypatch.setattr(gate, "_take_balanced", small_take)
    report = gate._train_one(
        train=rows,
        validation=rows,
        initialization_seed=2026112101,
        lineage=gate.SOURCE_LINEAGES[0],
        destination=tmp_path / "checkpoint-run",
    )
    assert report["train_rows_by_context"]["12"]["rows"] == 2
    assert report["train_rows_by_context"]["12"]["one_action_rows"] == 1
    checkpoint_path = Path(report["rungs"]["1"]["checkpoint"])
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    assert payload["schema"] == gate.CHECKPOINT_SCHEMA
    assert payload["runner_schema"] == gate.RUNNER_SCHEMA
    assert payload["claim_ceiling"] == gate.CLAIM_CEILING
    assert payload["q3"]["algorithm"] == "multi-catfish-mcrl-b402-c3-softkl"
    assert payload["test_split_opened"] is False
    assert payload["held_out_ee_evaluated"] is False
    assert payload["episode_training"] is False


def test_run_persists_source_only_result_flags_and_objective(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_rows = _rows(anchors=1, users=1)

    def fake_load(
        _paths: object, *, lineage: int, worlds: tuple[int, ...]
    ) -> gate.ReferenceRows:
        del lineage
        receipts = tuple(
            {
                "world_seed": int(world),
                "field_root_digest": "f" * 64,
            }
            for world in worlds
        )
        return replace(base_rows, shard_receipts=receipts)

    def fake_train_one(
        *,
        train: gate.ReferenceRows,
        validation: gate.ReferenceRows,
        initialization_seed: int,
        lineage: int,
        destination: Path,
    ) -> dict[str, object]:
        del destination
        return {
            "initialization_seed": initialization_seed,
            "source_lineage": lineage,
            "train_rows": train.rows,
            "validation_rows": validation.rows,
            "train_source_sha256": "a" * 64,
            "validation_source_sha256": "b" * 64,
            "state_alias_diagnostics": {},
            "train_rows_by_context": {},
            "rungs": {"3000": {"decision": {"passed": True}}},
        }

    monkeypatch.setattr(gate, "load_reference_rows", fake_load)
    monkeypatch.setattr(gate, "_train_one", fake_train_one)
    result = gate.run(source_paths=(), output_dir=tmp_path / "result")
    assert result["schema"] == gate.RESULT_SCHEMA
    assert result["runner_schema"] == gate.RUNNER_SCHEMA
    assert result["claim_ceiling"] == gate.CLAIM_CEILING
    assert result["source_only"] is True
    assert result["test_split_opened"] is False
    assert result["held_out_ee_evaluated"] is False
    assert result["episode_training"] is False
    assert result["decision"] == "PASS_SOFTKL_GATE"
    assert result["objective"] == {
        "name": "masked-row-mean-soft-teacher-kl",
        "temperature": 1.0,
        "reference_gauge_beta": 0.1,
        "all_legal_actions": True,
        "one_action_rows_included": True,
    }
    persisted = json.loads(
        (tmp_path / "result" / "result.json").read_text(encoding="ascii")
    )
    assert persisted["source_only"] is True
    assert persisted["test_split_opened"] is False
    assert persisted["held_out_ee_evaluated"] is False
    assert persisted["episode_training"] is False
