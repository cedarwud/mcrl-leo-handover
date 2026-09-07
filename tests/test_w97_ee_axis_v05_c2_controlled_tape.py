"""W-97 -- V0.5 controlled physical-tape seam."""

from __future__ import annotations

from dataclasses import replace
import hashlib

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable
from mcrl.runtime.ee_axis_v05_c2_controlled_tape import (
    CONTROLLED_TAPE_FADING_MODE,
    ControlledTapeContractError,
    build_controlled_tape_target,
    build_reference_action_tape,
    remap_controlled_tape_pair,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _table(bindings: dict[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in bindings.items():
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norad_ids=norads, cell_ids=cells, mask=mask)


def _physical_steps() -> list[list[tuple[int, int]]]:
    return [
        [(100, 0), (200, 0), (300, 0)],
        [(100, 1), (200, 1), (300, 1)],
        [(100, 2), (200, 2), (300, 2)],
        [(100, 3), (200, 3), (300, 3)],
    ]


def _trace() -> list[dict[str, object]]:
    physical = _physical_steps()
    return [
        {
            "offset": offset,
            "executed_actions": [0, 1, 2],
            "executed_physical_actions": step,
        }
        for offset, step in enumerate(physical)
    ]


def _tape():
    return build_reference_action_tape(
        _trace(),
        anchor_sha256=digest("anchor"),
        reference_policy_sha256=digest("q13-policy"),
        common_random_field_sha256=digest("crf"),
        focal_user=0,
    )


def _branch_tables(*, include_hold_until: int = 3) -> tuple[list[list[SlotTable]], list[list[SlotTable]]]:
    physical = _physical_steps()
    reference: list[list[SlotTable]] = []
    candidate: list[list[SlotTable]] = []
    for offset, keys in enumerate(physical):
        # Branch-local slot indices intentionally differ from the reference
        # indices.  Equality must therefore be checked by physical key.
        reference.append(
            [
                _table({5: keys[0]}),
                _table({6: keys[1]}),
                _table({7: keys[2]}),
            ]
        )
        candidate_focal = {8: keys[0]}
        if offset < include_hold_until:
            candidate_focal[9] = (999, 9)
        candidate.append(
            [
                _table(candidate_focal),
                _table({10: keys[1]}),
                _table({11: keys[2]}),
            ]
        )
    return reference, candidate


def test_reference_tape_is_physical_and_digest_bound() -> None:
    tape = _tape()

    assert tape.fading_mode == CONTROLLED_TAPE_FADING_MODE
    assert tape.user_count == 3
    assert tape.steps[1].physical_actions[1] == (200, 1)
    assert tape.verify() == tape.tape_sha256
    assert tape.as_mapping()["tape_sha256"] == tape.tape_sha256


def test_reference_trace_digest_mismatch_fails_closed() -> None:
    with pytest.raises(ControlledTapeContractError, match="actual reference trace"):
        build_reference_action_tape(
            _trace(),
            anchor_sha256=digest("anchor"),
            reference_policy_sha256=digest("q13-policy"),
            common_random_field_sha256=digest("crf"),
            reference_trace_sha256=digest("unrelated-trace"),
            focal_user=0,
        )


def test_remap_uses_branch_local_slots_but_preserves_nonfocal_physical_identity() -> None:
    tape = _tape()
    reference, candidate = _branch_tables()

    plan = remap_controlled_tape_pair(
        tape,
        reference,
        candidate,
        held_physical_key=(999, 9),
        release_offset=3,
        release_reason="horizon",
        support_counts=(1, 1, 1, 1),
    )

    assert plan.verify(tape) == plan.plan_sha256
    for step in plan.steps:
        assert step.nonfocal_equal
        assert step.reference_physical_actions[1:] == step.candidate_physical_actions[1:]
        assert step.nonfocal_equality_sha256
    # Slot indices differ, while physical actions remain identical for users 1/2.
    assert plan.steps[0].reference_actions[1:] == (6, 7)
    assert plan.steps[0].candidate_actions[1:] == (10, 11)


def test_focal_hold_then_release_is_the_only_allowed_divergence() -> None:
    tape = _tape()
    reference, candidate = _branch_tables(include_hold_until=2)

    plan = remap_controlled_tape_pair(
        tape,
        reference,
        candidate,
        held_physical_key=(999, 9),
        release_offset=2,
        release_reason="support_expired",
        support_counts=(1, 1, 0, 0),
    )

    assert [step.focal_mode for step in plan.steps] == ["hold", "hold", "released", "released"]
    assert plan.steps[0].candidate_physical_actions[0] == (999, 9)
    assert plan.steps[1].candidate_physical_actions[0] == (999, 9)
    assert plan.steps[2].candidate_physical_actions[0] == (100, 2)
    assert plan.steps[3].candidate_physical_actions[0] == (100, 3)


@pytest.mark.parametrize(
    "mutator, pattern",
    [
        ("missing", "missing"),
        ("duplicate", "duplicated"),
    ],
)
def test_missing_or_duplicated_required_physical_key_fails_closed(
    mutator: str, pattern: str
) -> None:
    tape = _tape()
    reference, candidate = _branch_tables()
    if mutator == "missing":
        candidate[0][1] = _table({10: (201, 0)})
    else:
        candidate[0][0] = _table({8: (100, 0), 9: (999, 9), 12: (999, 9)})

    with pytest.raises(ControlledTapeContractError, match=pattern):
        remap_controlled_tape_pair(
            tape,
            reference,
            candidate,
            held_physical_key=(999, 9),
            release_offset=3,
            release_reason="horizon",
            support_counts=(1, 1, 1, 1),
        )


def test_support_expiry_requires_first_zero_and_has_no_fallback() -> None:
    tape = _tape()
    reference, candidate = _branch_tables(include_hold_until=2)

    with pytest.raises(ControlledTapeContractError, match="first zero"):
        remap_controlled_tape_pair(
            tape,
            reference,
            candidate,
            held_physical_key=(999, 9),
            release_offset=2,
            release_reason="support_expired",
            support_counts=(1, 0, 0, 0),
        )

    # The release row must still remap the taped focal key.  Removing it is a
    # hard error; the seam must not invent a branch-local fallback.
    candidate[2][0] = _table({8: (101, 2)})
    with pytest.raises(ControlledTapeContractError, match="missing"):
        remap_controlled_tape_pair(
            tape,
            reference,
            candidate,
            held_physical_key=(999, 9),
            release_offset=2,
            release_reason="support_expired",
            support_counts=(1, 1, 0, 0),
        )


@pytest.mark.parametrize(
    "release_reason, release_offset, support_counts, pattern",
    [
        ("horizon", 3, (1, 2, 1, 1), "exactly one"),
        ("horizon", 2, (1, 1, 1, 1), "offset 3"),
        ("support_expired", 2, (1, 1, 0, 2), "ambiguous"),
        ("support_expired", 2, (1, 2, 0, 0), "exactly one"),
    ],
)
def test_support_receipt_is_unique_and_horizon_complete(
    release_reason: str,
    release_offset: int,
    support_counts: tuple[int, ...],
    pattern: str,
) -> None:
    tape = _tape()
    reference, candidate = _branch_tables(
        include_hold_until=release_offset if release_reason == "support_expired" else 3,
    )
    if release_reason == "support_expired":
        # The synthetic candidate has support exactly through the declared
        # release offset and uses the taped focal key after release.
        candidate[release_offset][0] = _table({8: _physical_steps()[release_offset][0]})
        if release_offset == 2:
            candidate[2][0] = _table({8: _physical_steps()[2][0]})
    with pytest.raises(ControlledTapeContractError, match=pattern):
        remap_controlled_tape_pair(
            tape,
            reference,
            candidate,
            held_physical_key=(999, 9),
            release_offset=release_offset,
            release_reason=release_reason,
            support_counts=support_counts,
        )


def test_support_receipt_is_required_even_for_horizon_release() -> None:
    tape = _tape()
    reference, candidate = _branch_tables()
    with pytest.raises(ControlledTapeContractError, match="support_counts are required"):
        remap_controlled_tape_pair(
            tape,
            reference,
            candidate,
            held_physical_key=(999, 9),
            release_offset=3,
            release_reason="horizon",
            support_counts=None,
        )


def test_nonfocal_receipt_rejects_tampering_after_remap() -> None:
    tape = _tape()
    reference, candidate = _branch_tables()
    plan = remap_controlled_tape_pair(
        tape,
        reference,
        candidate,
        held_physical_key=(999, 9),
        release_offset=3,
        release_reason="horizon",
        support_counts=(1, 1, 1, 1),
    )
    damaged_step = replace(
        plan.steps[0],
        candidate_physical_actions=((999, 9), (201, 0), (300, 0)),
    )
    damaged = replace(plan, steps=(damaged_step,) + plan.steps[1:])
    with pytest.raises(ControlledTapeContractError, match="nonfocal physical action|receipt"):
        damaged.verify(tape)


def test_controlled_target_keeps_raw_rate_energy_offsets_sum_and_mean() -> None:
    reference_rates = np.asarray(
        [[10.0, 20.0], [11.0, 19.0], [12.0, 18.0], [13.0, 17.0]],
        dtype=np.float64,
    )
    candidate_rates = np.asarray(
        [[10.0, 20.0], [13.0, 18.0], [10.0, 22.0], [15.0, 16.0]],
        dtype=np.float64,
    )
    reference_power = np.asarray([5.0, 5.0, 6.0, 7.0], dtype=np.float64)
    candidate_power = np.asarray([5.0, 5.5, 5.0, 8.0], dtype=np.float64)

    target = build_controlled_tape_target(
        tape_sha256=digest("tape"),
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        lambda_bits_per_j=2.0,
        interval_s=0.5,
    )

    # Offset 1: rate delta 1, energy delta .25 => .5 - .5 = 0.
    # Offset 2: rate delta 2, energy delta -.5 => 1 + 1 = 2.
    # Offset 3: rate delta 1, energy delta .5 => .5 - 1 = -.5.
    assert target.offset_rate_delta_bps.tolist() == [[2.0, -1.0], [-2.0, 4.0], [2.0, -1.0]]
    assert target.offset_system_energy_delta_j.tolist() == [0.25, -0.5, 0.5]
    assert target.offset_surplus_bits.tolist() == pytest.approx([0.0, 2.0, -0.5])
    assert target.zeta2_temporal_surplus_bits == pytest.approx(1.5)
    assert target.mean_offset_surplus_bits == pytest.approx(0.5)
    assert target.verify() == target.target_sha256

    meanless = build_controlled_tape_target(
        tape_sha256=digest("tape"),
        reference_rates_bps=reference_rates,
        candidate_rates_bps=candidate_rates,
        reference_system_power_w=reference_power,
        candidate_system_power_w=candidate_power,
        lambda_bits_per_j=2.0,
        interval_s=0.5,
        include_mean=False,
    )
    assert meanless.mean_offset_surplus_bits is None
    assert meanless.verify() == meanless.target_sha256


def test_tape_and_target_arrays_are_mutation_safe() -> None:
    tape = _tape()
    assert isinstance(tape.steps[0].physical_actions, tuple)
    with pytest.raises(TypeError):
        tape.steps[0].physical_actions[0][0] = 999  # type: ignore[index]

    target = build_controlled_tape_target(
        tape_sha256=digest("tape"),
        reference_rates_bps=np.ones((4, 2), dtype=np.float64),
        candidate_rates_bps=np.ones((4, 2), dtype=np.float64),
        reference_system_power_w=np.ones(4, dtype=np.float64),
        candidate_system_power_w=np.ones(4, dtype=np.float64),
        lambda_bits_per_j=1.0,
        interval_s=1.0,
    )
    assert not target.offset_rate_delta_bps.flags.writeable
    with pytest.raises(ValueError):
        target.offset_rate_delta_bps[0, 0] = 1.0
