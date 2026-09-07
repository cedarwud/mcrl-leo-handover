"""W-125 -- development-only V0.7 C2 B1 live-adapter mechanics."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

from mcrl.env.action_contract import NUM_ACTIONS, SlotTable


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / ".scratch" / "c3-v04" / "v07_c2_b1_fast_live.py"
SPEC = importlib.util.spec_from_file_location("v07_c2_b1_fast_live", LIVE)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def _table(*entries: tuple[int, tuple[int, int]]) -> SlotTable:
    norads = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    cells = np.full(NUM_ACTIONS, -1, dtype=np.int64)
    mask = np.zeros(NUM_ACTIONS, dtype=np.bool_)
    for action, (norad, cell) in entries:
        norads[action] = norad
        cells[action] = cell
        mask[action] = True
    return SlotTable(norads, cells, mask)


class _Observation:
    def __init__(self, tables: tuple[SlotTable, ...]) -> None:
        self.candidates = type("Candidates", (), {"slot_tables": tables})()


class _Evaluation:
    def __init__(self, power: float) -> None:
        self.system_power_w = power


class _Outcome:
    def __init__(
        self,
        observation: _Observation,
        *,
        rates: list[float],
        power: float,
    ) -> None:
        self.observation = observation
        self.link_rate_bps = np.asarray(rates, dtype=np.float64)
        self.system_power_w = power


class _Branch:
    """Small stateful branch stub with the real adapter-facing seams."""

    def __init__(self, tables: tuple[tuple[SlotTable, ...], ...], *, base: float) -> None:
        self.environment = self
        self._tables = tables
        self._base = base
        self._successor_index = -1
        self.last_outcome = _Outcome(
            _Observation(tables[0]),
            rates=[0.0, 0.0],
            power=base,
        )
        self.calls: list[tuple[str, int, tuple[int, ...]]] = []
        self.without_calls: list[tuple[int, tuple[int, ...]]] = []

    def _successor_outcome(self, *, removed: bool, done: bool) -> _Outcome:
        index = self._successor_index
        # The values are intentionally simple but distinct, so the returned
        # B1 target proves that the raw committed and without-focal terms were
        # passed through independently.
        focal_rate = 0.0 if removed else 10.0 + float(index)
        next_table = self._tables[min(index + 2, len(self._tables) - 1)]
        return _Outcome(
            _Observation(next_table),
            rates=[focal_rate, 7.0],
            power=self._base + float(index),
        )

    def reset_opening(self) -> None:
        self._successor_index = -1
        self.last_outcome = _Outcome(
            _Observation(self._tables[0]),
            rates=[0.0, 0.0],
            power=self._base,
        )

    def step(self, actions: np.ndarray, _rng: object):
        selected = tuple(int(value) for value in np.asarray(actions).tolist())
        if self._successor_index == -1:
            self.calls.append(("opening", 0, selected))
            self._successor_index = 0
            self.last_outcome = _Outcome(
                _Observation(self._tables[1]),
                rates=[0.0, 0.0],
                power=self._base,
            )
            return type("Result", (), {"done": False})()
        offset = self._successor_index + 1
        self.calls.append(("step", offset, selected))
        self.last_outcome = self._successor_outcome(removed=False, done=offset == 3)
        self._successor_index += 1
        return type("Result", (), {"done": offset == 3})()

    def step_without_user(self, actions: np.ndarray, _rng: object, *, focal_user: int):
        assert focal_user == 0
        selected = tuple(int(value) for value in np.asarray(actions).tolist())
        offset = self._successor_index + 1
        self.calls.append(("remove", offset, selected))
        self.last_outcome = self._successor_outcome(removed=True, done=offset == 3)
        self._successor_index += 1
        return type("Result", (), {"done": offset == 3})()

    def evaluate_actions_without_user(
        self,
        actions: np.ndarray,
        _rng: object,
        *,
        focal_user: int,
    ) -> _Evaluation:
        assert focal_user == 0
        offset = self._successor_index + 1
        selected = tuple(int(value) for value in np.asarray(actions).tolist())
        self.without_calls.append((offset, selected))
        return _Evaluation(self._base - 5.0 + float(offset))


def _fixtures() -> tuple[_Branch, _Branch, mod.B1PhysicalActionTape]:
    nonfocal = (200, 0)
    reference_keys = ((100, 0), (100, 1), (100, 2))
    held = (101, 1)
    carrier = (102, 2)

    # Entry 0 is the pre-opening table.  Entries 1..3 are the post-opening
    # tables visible before successor offsets 1..3.  The reference keeps its
    # tape focal key legal.  The candidate loses the held key after k=1 and
    # retains a legal carrier action only for the removal validation seam.
    reference_tables = tuple(
        (
            _table((0, key)),
            _table((1, nonfocal)),
        )
        for key in reference_keys
    )
    candidate_tables = (
        (_table((2, held)), _table((1, nonfocal))),
        (_table((0, held)), _table((1, nonfocal))),
        (_table((3, carrier)), _table((1, nonfocal))),
        (_table((3, carrier)), _table((1, nonfocal))),
        (_table((3, carrier)), _table((1, nonfocal))),
    )
    # Reference has one opening table plus one table for each successor.  The
    # first reference table only supports the opening action; all successor
    # tables are represented by the rows above.
    reference_branch_tables = (
        (_table((0, reference_keys[0])), _table((1, nonfocal))),
        reference_tables[0],
        reference_tables[1],
        reference_tables[2],
    )
    candidate_branch = _Branch(candidate_tables, base=90.0)
    reference_branch = _Branch(reference_branch_tables, base=100.0)

    tape = mod.precommit_q13_nonfocal_tape(
        reference_actions=(
            np.asarray([0, 1], dtype=np.int64),
            np.asarray([0, 1], dtype=np.int64),
            np.asarray([0, 1], dtype=np.int64),
        ),
        reference_slot_tables=reference_tables,
        focal_user=0,
    )
    return reference_branch, candidate_branch, tape


def test_precommit_tape_is_physical_and_exactly_three_offsets() -> None:
    _reference, _candidate, tape = _fixtures()

    assert tape.physical_actions == (
        ((100, 0), (200, 0)),
        ((100, 1), (200, 0)),
        ((100, 2), (200, 0)),
    )
    assert tape.tape_sha256 == tape.tape_sha256
    with pytest.raises(mod.B1FastLiveError, match="exactly offsets"):
        mod.B1PhysicalActionTape(
            physical_actions=tape.physical_actions[:2],
            focal_user=0,
        )


def test_capture_holds_then_uses_absorbing_removal_and_passes_raw_terms() -> None:
    reference, candidate, tape = _fixtures()
    capture = mod.capture_b1_pair(
        reference_branch=reference,
        candidate_branch=candidate,
        reference_rng=np.random.default_rng(1),
        candidate_rng=np.random.default_rng(2),
        reference_opening_actions=np.asarray([0, 1], dtype=np.int64),
        candidate_opening_actions=np.asarray([2, 1], dtype=np.int64),
        reference_opening_physical_actions=((100, 0), (200, 0)),
        candidate_opening_physical_actions=((101, 1), (200, 0)),
        reference_tape=tape,
        focal_user=0,
        lambda_bits_per_j=2.0,
        interval_s=1.0,
        focal_removal_validation_action=lambda _branch, _observation, _offset: 3,
    )

    assert capture.successor_offsets == (1, 2, 3)
    assert capture.candidate_modes == ("hold", "removed", "removed")
    assert capture.candidate_support_counts == (1, 0, 0)
    assert capture.removal_validation_actions == (None, 3, 3)
    assert [entry[0] for entry in candidate.calls] == ["opening", "step", "remove", "remove"]
    assert [entry[1] for entry in candidate.calls[1:]] == [1, 2, 3]
    assert capture.target.candidate_focal_rates_bps == (10.0, 0.0, 0.0)
    assert capture.target.reference_focal_rates_bps == (10.0, 11.0, 12.0)
    assert capture.target.candidate_full_power_w == (90.0, 91.0, 92.0)
    assert capture.target.reference_full_power_w == (100.0, 101.0, 102.0)
    assert capture.target.candidate_without_focal_power_w == (86.0, 87.0, 88.0)
    assert capture.target.reference_without_focal_power_w == (96.0, 97.0, 98.0)
    assert capture.claim_ceiling.startswith("development-only")
    assert capture.training_run is False
    assert capture.held_out_ee_evaluated is False
    assert capture.target_or_ee_selected is False


def test_opening_nonfocal_difference_is_rejected_before_any_step() -> None:
    reference, candidate, tape = _fixtures()
    with pytest.raises(mod.B1FastLiveError, match="focal user only"):
        mod.capture_b1_pair(
            reference_branch=reference,
            candidate_branch=candidate,
            reference_rng=np.random.default_rng(1),
            candidate_rng=np.random.default_rng(2),
            reference_opening_actions=np.asarray([0, 1], dtype=np.int64),
            candidate_opening_actions=np.asarray([2, 2], dtype=np.int64),
            reference_opening_physical_actions=((100, 0), (200, 0)),
            candidate_opening_physical_actions=((101, 1), (201, 0)),
            reference_tape=tape,
            focal_user=0,
            lambda_bits_per_j=2.0,
            interval_s=1.0,
        )
    assert reference.calls == []
    assert candidate.calls == []


def test_release_without_carrier_is_structural_failure_not_fallback() -> None:
    reference, candidate, tape = _fixtures()
    with pytest.raises(mod.B1FastLiveError, match="no removal validation action"):
        mod.capture_b1_pair(
            reference_branch=reference,
            candidate_branch=candidate,
            reference_rng=np.random.default_rng(1),
            candidate_rng=np.random.default_rng(2),
            reference_opening_actions=np.asarray([0, 1], dtype=np.int64),
            candidate_opening_actions=np.asarray([2, 1], dtype=np.int64),
            reference_opening_physical_actions=((100, 0), (200, 0)),
            candidate_opening_physical_actions=((101, 1), (200, 0)),
            reference_tape=tape,
            focal_user=0,
            lambda_bits_per_j=2.0,
            interval_s=1.0,
        )
    assert [entry[0] for entry in candidate.calls] == ["opening", "step"]
