"""Deterministic contract probes for the V0.5 controlled-source runner."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v05_c2_controlled_source",
    REPO / ".scratch/c3-v04/run_v05_c2_controlled_source.py",
)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _focal(*, seed: int, step: int, focal_user: int) -> object:
    reference_action = 0
    actions = tuple(range(1, NUM_ACTIONS))
    base = 900000 + seed % 1000
    keys = tuple((base + action, action) for action in actions)
    return runner.support.C2V04TopologyFocal(
        focal_user=focal_user,
        anchor_sha256=digest(f"anchor-{seed}-{step}-{focal_user}"),
        reference_action=reference_action,
        reference_physical_key=(base, reference_action),
        incumbent_physical_key=(base + 1000 + focal_user, focal_user),
        common_random_field_sha256=digest(f"field-{seed}-{step}-{focal_user}"),
        predecision_heuristic_scores=tuple(float(action) for action in actions),
        legal_action_mask=tuple(True for _ in range(NUM_ACTIONS)),
        candidate_actions=actions,
        candidate_physical_keys=keys,
    )


def _topology(seed: int, *, step: int) -> object:
    users = (0, 1, 2, 3)
    return runner.support.C2V04TopologyAnchor(
        source_seed=seed,
        step_index=step,
        world_anchor_sha256=digest(f"world-{seed}-{step}"),
        focal_candidates=tuple(
            _focal(seed=seed, step=step, focal_user=user) for user in users
        ),
        physical_main_departures=users,
        checkpoint_sha256=digest("checkpoint"),
        source_manifest_sha256=digest("manifest"),
        policy_sha256=digest("policy"),
        evaluation_seed=seed,
        common_random_field_root_sha256=digest(f"root-{seed}"),
        complete_forecast_horizon=True,
    )


def _args(output_file: Path) -> argparse.Namespace:
    return argparse.Namespace(
        output_file=str(output_file),
        phase_a_dir="unused",
        prereg="unused",
        tle_root="unused",
    )


def test_step_stratum_filter_is_applied_at_main_decision_boundary(monkeypatch) -> None:
    observed: list[tuple[str, int]] = []
    backend = SimpleNamespace()
    pair = SimpleNamespace()

    def main_decision(*args):
        observation = args[4]
        observed.append(("main", observation.step_index))
        return "main-action"

    def departure_users(*_args):
        observed.append(("departure", 0))
        return (1, 2)

    backend._main_decision = main_decision
    pair._departure_users = departure_users
    modules = {"backend_smoke": backend, "pair_smoke": pair}
    scanner_views: list[object] = []

    def scan(*, source_seed, modules, context):
        scanner_views.append(modules)
        for step in (1, 3):
            observation = SimpleNamespace(step_index=step)
            modules["backend_smoke"]._main_decision(
                None, None, None, None, observation, None
            )
            departures = modules["pair_smoke"]._departure_users(None, None)
            assert (departures if step == 3 else ()) == ((1, 2) if step == 3 else ())
        return ()

    monkeypatch.setattr(runner.support, "_real_seed_topology", scan)
    assert runner._real_seed_topology_for_steps(
        source_seed=1,
        modules=modules,
        context={},
        eligible_steps=frozenset({3}),
    ) == ()
    assert observed == [("main", 1), ("departure", 0), ("main", 3), ("departure", 0)]
    assert scanner_views and scanner_views[0]["backend_smoke"] is not backend
    with pytest.raises(runner.ControlledSourceError, match="eligible_steps"):
        runner._real_seed_topology_for_steps(
            source_seed=1,
            modules=modules,
            context={},
            eligible_steps={3},  # type: ignore[arg-type]
        )


def test_prepare_authenticates_three_strata_and_exact_12_by_324_census(
    monkeypatch, tmp_path: Path
) -> None:
    first_seeds = (2026093001, 2026093011, 2026093021)
    calls: list[tuple[int, frozenset[int]]] = []

    monkeypatch.setattr(runner, "_authenticate_common", lambda _args: ({}, {}))
    monkeypatch.setattr(runner.support, "_production_main_context", lambda **_kwargs: {})

    def scan(*, source_seed, modules, context, eligible_steps):
        calls.append((source_seed, eligible_steps))
        if source_seed in first_seeds:
            return (_topology(source_seed, step=min(eligible_steps)),)
        return ()

    monkeypatch.setattr(runner, "_real_seed_topology_for_steps", scan)
    output = tmp_path / "prepare.json"
    result = runner._prepare(_args(output))
    assert result["status"] == "CONTROLLED_SOURCE_SCHEDULE_PREPARED"
    assert calls == [
        (first_seeds[0], frozenset({1, 2})),
        (first_seeds[1], frozenset({3, 4})),
        (first_seeds[2], frozenset({5, 6})),
    ]
    receipt, schedule, _file_sha = runner._read_prepare(output)
    assert len(schedule.anchors) == 12
    assert len(schedule.rows) == 324
    assert sorted({anchor.anchor_step for anchor in schedule.anchors}) == [1, 3, 5]
    assert receipt["policy_views"] == [
        "main",
        "q13-2026092101",
        "q13-2026092102",
        "q13-2026092103",
    ]


def test_prepare_rejects_self_consistent_wrong_stratum_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    first_seeds = (2026093001, 2026093011, 2026093021)
    monkeypatch.setattr(runner, "_authenticate_common", lambda _args: ({}, {}))
    monkeypatch.setattr(runner.support, "_production_main_context", lambda **_kwargs: {})
    monkeypatch.setattr(
        runner,
        "_real_seed_topology_for_steps",
        lambda *, source_seed, **_kwargs: (
            (_topology(source_seed, step={first_seeds[0]: 1, first_seeds[1]: 3, first_seeds[2]: 5}[source_seed]),)
            if source_seed in first_seeds
            else ()
        ),
    )
    output = tmp_path / "prepare.json"
    runner._prepare(_args(output))
    payload = json.loads(output.read_text(encoding="ascii"))
    payload["strata"][0]["eligible_steps"] = [2, 3]
    payload["prepare_sha256"] = runner._canonical_sha256(
        {key: value for key, value in payload.items() if key != "prepare_sha256"}
    )
    output.write_bytes(runner._canonical_bytes(payload))
    with pytest.raises(runner.ControlledSourceError, match="stratum e definition"):
        runner._read_prepare(output)


def test_write_once_preserves_winner_when_race_creates_final_path(monkeypatch, tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    original_link = runner.os.link

    def race(source, destination):
        Path(destination).write_bytes(b"winner")
        return original_link(source, destination)

    monkeypatch.setattr(runner.os, "link", race)
    with pytest.raises(runner.ControlledSourceError, match="refusing to overwrite"):
        runner._write_once(target, {"schema": "synthetic"})
    assert target.read_bytes() == b"winner"


def test_read_json_rejects_symlinked_receipt(tmp_path: Path) -> None:
    real = tmp_path / "real.json"
    real.write_bytes(runner._canonical_bytes({"schema": "synthetic"}))
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(runner.ControlledSourceError, match="non-regular"):
        runner._read_json(link)


def _slot_table(bindings: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in bindings.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norad_ids=norads, cell_ids=cells, mask=mask)


def _valid_row() -> tuple[object, dict[str, object], tuple[int, int]]:
    anchor = _topology(2026093001, step=1).selected_anchor_schedules()[0]
    candidate_key = tuple(anchor.candidate_physical_keys[0])
    base = anchor.reference_physical_key[0]
    reference_physical = [
        [(base, 0), (base + 100, 0)],
        [(base, 1), (base + 100, 1)],
        [(base, 2), (base + 100, 2)],
        [(base, 3), (base + 100, 3)],
    ]
    reference_actions = [[0, 1] for _ in range(4)]
    held = [list(candidate_key)] * 3
    candidate_physical = [
        [list(candidate_key), list(reference_physical[offset][1])]
        if offset < 3
        else [list(reference_physical[offset][0]), list(reference_physical[offset][1])]
        for offset in range(4)
    ]
    reference_tables = [
        [_slot_table({0: tuple(reference_physical[offset][0])}), _slot_table({1: tuple(reference_physical[offset][1])})]
        for offset in range(4)
    ]
    candidate_tables = [
        [
            _slot_table(
                {
                    2: candidate_key,
                    3: tuple(reference_physical[offset][0]),
                }
                if offset < 3
                else {3: tuple(reference_physical[offset][0])}
            ),
            _slot_table({4: tuple(reference_physical[offset][1])}),
        ]
        for offset in range(4)
    ]
    tape = runner.mechanics.controlled.build_reference_action_tape(
        {
            "offsets": [0, 1, 2, 3],
            "executed_actions": reference_actions,
            "executed_physical_actions": reference_physical,
        },
        anchor_sha256=anchor.anchor_sha256,
        reference_policy_sha256=digest("main-components"),
        common_random_field_sha256=anchor.common_random_field_sha256,
        focal_user=anchor.focal_user,
    )
    plan = runner.mechanics.controlled.remap_controlled_tape_pair(
        tape,
        reference_tables,
        candidate_tables,
        held_physical_key=candidate_key,
        release_offset=3,
        release_reason="horizon",
        support_counts=(1, 1, 1, 1),
    )
    candidate_actions = [list(step.candidate_actions) for step in plan.steps]
    state_digests = [digest(f"state-{offset}") for offset in range(4)]
    mask_digests = [digest(f"mask-{offset}") for offset in range(4)]

    def trace(*, candidate: bool) -> dict[str, object]:
        physical = candidate_physical if candidate else reference_physical
        actions = candidate_actions if candidate else reference_actions
        return {
            "active_physical_ids": [[list(key) for key in row] for row in physical],
            "detached_main_actions": actions,
            "detached_main_physical_actions": physical,
            "done": [False] * 4,
            "executed_actions": actions,
            "executed_physical_actions": physical,
            "held_key_match_count": [1, 1, 1, 1] if candidate else [None] * 4,
            "held_physical_key": [list(candidate_key)] * 4 if candidate else [None] * 4,
            "link_rate_bps": [[1.0, 2.0], [1.0, 2.0], [1.0, 2.0], [1.0, 2.0]]
            if not candidate
            else [[1.0, 2.0], [2.0, 2.0], [1.0, 2.0], [1.0, 2.0]],
            "mask_matrix_sha256": mask_digests,
            "offsets": [0, 1, 2, 3],
            "release_offset": [3] * 4 if candidate else [None] * 4,
            "release_reason": ["horizon"] * 4 if candidate else [None] * 4,
            "served": [[True, True] for _ in range(4)],
            "state_matrix_sha256": state_digests,
            "system_power_w": [1.0, 1.0, 1.0, 1.0]
            if not candidate
            else [1.0, 1.5, 1.0, 1.0],
        }

    reference = trace(candidate=False)
    candidate = trace(candidate=True)
    components = runner.mechanics._reference_policy_components(
        tape_policy="main",
        main_policy_sha256=anchor.policy_sha256,
        hybrid=None,
        initialization_seed=None,
    )
    policy_sha = components["policy_components_sha256"]
    tape_map = dict(tape.as_mapping())
    # Rebuild the tape with the policy receipt actually persisted by the row.
    tape = runner.mechanics.controlled.build_reference_action_tape(
        reference,
        anchor_sha256=anchor.anchor_sha256,
        reference_policy_sha256=policy_sha,
        common_random_field_sha256=anchor.common_random_field_sha256,
        focal_user=anchor.focal_user,
    )
    plan = runner.mechanics.controlled.remap_controlled_tape_pair(
        tape,
        reference_tables,
        candidate_tables,
        held_physical_key=candidate_key,
        release_offset=3,
        release_reason="horizon",
        support_counts=(1, 1, 1, 1),
    )
    candidate["executed_actions"] = [list(step.candidate_actions) for step in plan.steps]
    candidate["detached_main_actions"] = candidate["executed_actions"]
    candidate["executed_physical_actions"] = [
        [None if key is None else list(key) for key in step.candidate_physical_actions]
        for step in plan.steps
    ]
    candidate["detached_main_physical_actions"] = candidate["executed_physical_actions"]
    candidate["active_physical_ids"] = candidate["executed_physical_actions"]
    target = runner.mechanics.controlled.build_controlled_tape_target(
        tape_sha256=tape.tape_sha256,
        reference_rates_bps=np.asarray(reference["link_rate_bps"], dtype=np.float64),
        candidate_rates_bps=np.asarray(candidate["link_rate_bps"], dtype=np.float64),
        reference_system_power_w=np.asarray(reference["system_power_w"], dtype=np.float64),
        candidate_system_power_w=np.asarray(candidate["system_power_w"], dtype=np.float64),
        lambda_bits_per_j=2.0,
        interval_s=0.5,
    )
    state, mask = np.zeros(228, dtype=np.float32), np.ones(28, dtype=np.bool_)
    anchor_state = runner.phase_b._anchor_state_record(
        state=state,
        mask=mask,
        state_schema=runner.phase_b.EE_AXIS_STATE_SCHEMA,
        state_schema_sha256=runner.phase_b.EE_AXIS_STATE_SCHEMA_SHA256,
        state_observation_sha256=digest("observation"),
    )
    row: dict[str, object] = {
        "schema": runner.ROW_SCHEMA,
        "source_route": "C2",
        "tape_policy": "main",
        "anchor_sha256": anchor.anchor_sha256,
        "anchor_schedule_sha256": anchor.anchor_schedule_sha256,
        "source_manifest_sha256": anchor.source_manifest_sha256,
        "source_seed": anchor.source_seed,
        "evaluation_seed": anchor.evaluation_seed,
        "initialization_seed": None,
        "focal_user": anchor.focal_user,
        "candidate_physical_key": list(candidate_key),
        "reference_policy_sha256": policy_sha,
        "reference_policy_components": components,
        "common_random_field_sha256": anchor.common_random_field_sha256,
        "tape": tape.as_mapping(),
        "pair_plan": plan.as_mapping(tape),
        "target": target.as_mapping(),
        "raw_trace": {
            "reference": reference,
            "candidate": candidate,
            "reference_policy_decisions": [
                {"offset": offset, "policy": "main", "actions": reference_actions[offset]}
                for offset in (1, 2, 3)
            ],
            "support_counts": [1, 1, 1, 1],
            "release_offset": 3,
            "release_reason": "horizon",
            "continuation_start_offset": 1,
        },
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "anchor_step": anchor.anchor_step,
        "anchor_state": anchor_state,
    }
    row["learner_pair"] = runner._learner_pair(row=row, anchor_state=anchor_state)
    return anchor, row, candidate_key


def test_source_row_binds_anchor_state_pair_and_main_policy_receipt() -> None:
    anchor, row, candidate_key = _valid_row()
    components = row["reference_policy_components"]
    runner._validate_source_row(
        row=row,
        anchor=anchor,
        candidate_key=candidate_key,
        tape_policy="main",
        initialization_seed=None,
        expected_policy_components=components,
    )
    damaged = dict(row)
    pair = dict(damaged["learner_pair"])
    pair["anchor_state_sha256"] = digest("wrong-state")
    damaged["learner_pair"] = pair
    with pytest.raises(runner.ControlledSourceError, match="learner pair"):
        runner._validate_source_row(
            row=damaged,
            anchor=anchor,
            candidate_key=candidate_key,
            tape_policy="main",
            initialization_seed=None,
            expected_policy_components=components,
        )


def test_source_row_rejects_row_policy_receipt_mismatch() -> None:
    anchor, row, candidate_key = _valid_row()
    damaged = dict(row)
    damaged["reference_policy_components"] = dict(row["reference_policy_components"])
    damaged["reference_policy_components"]["main_policy_sha256"] = digest("wrong-policy")
    with pytest.raises(runner.ControlledSourceError, match="policy"):
        runner._validate_source_row(
            row=damaged,
            anchor=anchor,
            candidate_key=candidate_key,
            tape_policy="main",
            initialization_seed=None,
            expected_policy_components=row["reference_policy_components"],
        )


def test_merge_rejects_a_self_consistent_shard_with_wrong_row_anchor(
    monkeypatch, tmp_path: Path
) -> None:
    anchor, valid_row, _candidate_key = _valid_row()
    schedule = SimpleNamespace(anchors=tuple(anchor for _ in range(12)))
    prepare = {
        "prepare_sha256": "prepare",
        "schedule": {"schedule_sha256": "schedule"},
    }
    damaged_row = dict(valid_row)
    damaged_row["anchor_sha256"] = digest("wrong-row-anchor")
    rows = [dict(valid_row) for _ in range(27)]
    rows[0] = damaged_row
    components = valid_row["reference_policy_components"]
    shard = {
        "schema": runner.SHARD_SCHEMA,
        "status": "CONTROLLED_SOURCE_SHARD_COMPLETE",
        "claim_ceiling": runner.CLAIM_CEILING,
        "prepare_file_sha256": "prepare-file",
        "prepare_sha256": "prepare",
        "schedule_sha256": "schedule",
        "anchor_index": 0,
        "anchor_sha256": anchor.anchor_sha256,
        "anchor_step": anchor.anchor_step,
        "tape_policy": "main",
        "initialization_seed": None,
        "reference_policy_components": components,
        "policy_parameters_unchanged": True,
        "row_count": 27,
        "rows": rows,
        "training_run": False,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "elapsed_s": 0.0,
    }
    shard["shard_sha256"] = runner._canonical_sha256(shard)
    monkeypatch.setattr(
        runner,
        "_read_prepare",
        lambda _path: (prepare, schedule, "prepare-file"),
    )
    monkeypatch.setattr(
        runner,
        "_read_json",
        lambda _path: (shard, "shard-file"),
    )
    args = argparse.Namespace(
        prepare_file="prepare.json",
        shard_dir=str(tmp_path),
        output_file=str(tmp_path / "merge.json"),
    )
    with pytest.raises(runner.ControlledSourceError, match="row anchor lineage"):
        runner._merge(args)
