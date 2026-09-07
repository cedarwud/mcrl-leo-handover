"""Outcome-blind V0.4 C3 schedule and action-support gates."""

from __future__ import annotations

from dataclasses import fields, replace
import hashlib
import json

import pytest

from mcrl.runtime import ee_axis_v04_c3_schedule as schedule_module
from mcrl.runtime.ee_axis_v04_c3_schedule import (
    C3V04ContextCandidate,
    C3V04ScheduleContractError,
    build_v04_c3_schedule,
    read_v04_c3_schedule,
    write_v04_c3_schedule,
)
from mcrl.runtime.ee_axis_v04_c3_selector import C3_V04_INFORMED_SOURCE_RULE


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _context(
    *,
    seed: int,
    split: str,
    index: int,
    reference: int,
    candidates: tuple[int, ...],
) -> C3V04ContextCandidate:
    row = C3V04ContextCandidate(
        source_seed=seed,
        split=split,
        anchor_sha256=_sha(f"anchor-{seed}-{index}"),
        state_observation_sha256=_sha(f"state-{seed}-{index}"),
        step_index=index,
        focal_user=index,
        source_rule=C3_V04_INFORMED_SOURCE_RULE,
        reference_action=reference,
        reference_physical_key=(10_000 + reference, 0),
        candidate_actions=candidates,
        candidate_physical_keys=tuple(
            (10_000 + action, action) for action in candidates
        ),
        burden_deltas=tuple(float(action - reference) for action in candidates),
        satellite_burden_deltas=tuple(
            float(action - reference) / 2.0 for action in candidates
        ),
        victim_pressures=tuple(float(action + 1) for action in candidates),
        satellite_victim_pressures=tuple(
            float(action + 2) for action in candidates
        ),
    )
    row.verify()
    return row


def _universe(*, unsupported_validation: bool = False):
    rows = []
    groups = tuple(tuple(range(start, min(start + 4, 28))) for start in range(1, 28, 4))
    for index, actions in enumerate(groups):
        rows.append(
            _context(
                seed=1 if index % 2 == 0 else 2,
                split="train",
                index=index,
                reference=0,
                candidates=actions,
            )
        )
    # Enough non-duplicate filler to satisfy five contexts per TRAIN seed.
    for seed in (1, 2):
        for offset in range(5):
            rows.append(
                _context(
                    seed=seed,
                    split="train",
                    index=100 + seed * 10 + offset,
                    reference=0,
                    candidates=(1 + offset,),
                )
            )
    for index in range(4):
        rows.append(
            _context(
                seed=3,
                split="validation",
                index=200 + index,
                reference=27 if unsupported_validation else 0,
                candidates=(23, 24, 25, 26) if unsupported_validation else (1, 2, 3, 4),
            )
        )
    return rows


def _build(rows=None):
    return build_v04_c3_schedule(
        _universe() if rows is None else rows,
        seed_split={1: "train", 2: "train", 3: "validation"},
        train_context_goal=10,
        validation_context_goal=3,
        train_row_budget=40,
        validation_row_budget=10,
    )


def test_schedule_connects_all_actions_caps_rows_and_supports_validation():
    schedule = _build()

    assert schedule.verify() == schedule.schedule_sha256
    assert len(schedule.train) == 10
    assert len(schedule.validation) == 3
    assert sum(len(row.candidate_actions) for row in schedule.train) <= 40
    assert sum(len(row.candidate_actions) for row in schedule.validation) == 10
    train_pairs = {pair for row in schedule.train for pair in row.directed_pairs}
    validation_pairs = {
        pair for row in schedule.validation for pair in row.directed_pairs
    }
    assert validation_pairs <= train_pairs
    assert {action for pair in train_pairs for action in pair} == set(range(28))
    assert not {"target", "reward", "rate", "ee"}.intersection(
        field.name for field in fields(C3V04ContextCandidate)
    )


def test_schedule_is_deterministic_and_round_trips_canonically(tmp_path):
    first = _build()
    second = _build(list(reversed(_universe())))
    assert first.schedule_sha256 == second.schedule_sha256

    path = tmp_path / "schedule.json"
    file_sha = write_v04_c3_schedule(path, first)
    assert file_sha == hashlib.sha256(path.read_bytes()).hexdigest()
    restored = read_v04_c3_schedule(path)
    assert restored == first
    with pytest.raises(FileExistsError):
        write_v04_c3_schedule(path, first)


def test_schedule_rejects_disconnected_train_graph():
    rows = [
        _context(
            seed=seed,
            split="train",
            index=seed * 10 + index,
            reference=0,
            candidates=(1, 2, 3, 4),
        )
        for seed in (1, 2)
        for index in range(5)
    ]
    rows.extend(
        _context(
            seed=3,
            split="validation",
            index=200 + index,
            reference=0,
            candidates=(1,),
        )
        for index in range(3)
    )
    with pytest.raises(C3V04ScheduleContractError, match="connected 28-action"):
        _build(rows)


def test_schedule_rejects_validation_without_train_pair_support():
    with pytest.raises(C3V04ScheduleContractError, match="TRAIN-supported"):
        _build(_universe(unsupported_validation=True))


def test_schedule_rejects_one_anchor_pseudoreplicating_a_seed_quota():
    rows = _universe()
    validation = [row for row in rows if row.split == "validation"]
    shared_anchor = validation[0].anchor_sha256
    shared_state = validation[0].state_observation_sha256
    crowded = [
        replace(
            row,
            anchor_sha256=shared_anchor,
            state_observation_sha256=shared_state,
            step_index=validation[0].step_index,
        )
        if row.split == "validation"
        else row
        for row in rows
    ]
    with pytest.raises(C3V04ScheduleContractError, match="anchor-balanced"):
        build_v04_c3_schedule(
            crowded,
            seed_split={1: "train", 2: "train", 3: "validation"},
            train_context_goal=10,
            validation_context_goal=3,
            train_row_budget=40,
            validation_row_budget=10,
            max_contexts_per_anchor=2,
        )


def test_schedule_digest_detects_serialized_tampering(tmp_path):
    schedule = _build()
    path = tmp_path / "schedule.json"
    write_v04_c3_schedule(path, schedule)
    payload = json.loads(path.read_text(encoding="ascii"))
    payload["validation"][0]["candidate_actions"][0] = 5
    path.write_text(json.dumps(payload), encoding="ascii")

    with pytest.raises(C3V04ScheduleContractError):
        read_v04_c3_schedule(path)


def test_default_263_203_context_and_1052_810_row_contract_closes():
    rows = []
    train_seeds = (10, 11, 12, 13)
    validation_seeds = (20, 21, 22)
    coverage_groups = tuple(
        tuple(range(start, min(start + 4, 28))) for start in range(1, 28, 4)
    )
    coverage_groups = (*coverage_groups[:-1], (*coverage_groups[-1], 1))
    for seed in train_seeds:
        for index in range(70):
            actions = coverage_groups[index] if seed == 10 and index < 7 else (1, 2, 3, 4)
            rows.append(
                _context(
                    seed=seed,
                    split="train",
                    index=index,
                    reference=0,
                    candidates=actions,
                )
            )
    for seed in validation_seeds:
        for index in range(70):
            rows.append(
                _context(
                    seed=seed,
                    split="validation",
                    index=index,
                    reference=0,
                    candidates=(1, 2, 3, 4),
                )
            )

    schedule = build_v04_c3_schedule(
        rows,
        seed_split={
            **{seed: "train" for seed in train_seeds},
            **{seed: "validation" for seed in validation_seeds},
        },
    )

    assert len(schedule.train) == 263
    assert len(schedule.validation) == 203
    assert sum(len(row.candidate_actions) for row in schedule.train) == 1052
    assert sum(len(row.candidate_actions) for row in schedule.validation) == 810
    assert schedule.verify() == schedule.schedule_sha256


def test_schedule_rank_keeps_beam_pressure_ahead_of_satellite_contrast():
    base = _context(
        seed=1,
        split="train",
        index=1,
        reference=0,
        candidates=(1,),
    )
    satellite_heavy = replace(
        base,
        anchor_sha256=_sha("satellite-heavy"),
        burden_deltas=(10.0,),
        victim_pressures=(20.0,),
        satellite_burden_deltas=(100.0,),
        satellite_victim_pressures=(100.0,),
    )
    beam_pressure_heavy = replace(
        base,
        anchor_sha256=_sha("beam-pressure-heavy"),
        burden_deltas=(10.0,),
        victim_pressures=(30.0,),
        satellite_burden_deltas=(1.0,),
        satellite_victim_pressures=(1.0,),
    )

    assert schedule_module._rank_key(beam_pressure_heavy) < (
        schedule_module._rank_key(satellite_heavy)
    )
