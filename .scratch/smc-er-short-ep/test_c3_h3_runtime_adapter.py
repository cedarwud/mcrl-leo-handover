"""Focused public-seam tests for the fail-closed C3 H3 runtime adapter."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
CORE_PATH = HERE.parent / "catfish-stage0" / "c3_reward_aligned_core.py"
ADAPTER_PATH = HERE / "c3_h3_runtime_adapter.py"

core_spec = importlib.util.spec_from_file_location("c3_reward_aligned_core", CORE_PATH)
assert core_spec.loader is not None
c3 = importlib.util.module_from_spec(core_spec)
sys.modules[core_spec.name] = c3
core_spec.loader.exec_module(c3)

adapter_spec = importlib.util.spec_from_file_location(
    "c3_h3_runtime_adapter", ADAPTER_PATH
)
assert adapter_spec.loader is not None
adapter = importlib.util.module_from_spec(adapter_spec)
sys.modules[adapter_spec.name] = adapter
adapter_spec.loader.exec_module(adapter)


SOURCE = (8, 1)
DESTINATION = (8, 2)
OTHER = (9, 1)
CHECKPOINT = "a" * 64
ANCHOR_FINGERPRINT = "c" * 64
WRONG_EQUAL_FINGERPRINT = "d" * 64


def _power(total: float) -> object:
    fixed = 3 * 0.338 + 2 * 0.200
    supply = (total - fixed) / 3.0
    return c3.PowerSnapshot(
        supply_power_w_by_beam={SOURCE: supply, DESTINATION: supply, OTHER: supply},
        radiating_beams_by_satellite={8: 2, 9: 1},
        reported_fixed_power_w=fixed,
        reported_system_power_w=total,
        pa_identity_residual_w=0.0,
    )


def _reference_actions() -> dict[int, tuple[int, int] | None]:
    actions: dict[int, tuple[int, int] | None] = {}
    for user in range(1, 4):
        actions[user] = SOURCE
    actions[4] = DESTINATION
    for user in range(5, 100):
        actions[user] = OTHER
    return actions


def _frame(interval: int, *, candidate: bool = False) -> object:
    reference_loads = {SOURCE: 4, DESTINATION: 1, OTHER: 95}
    loads = (
        c3.expected_candidate_loads(
            reference_loads, source_id=SOURCE, destination_id=DESTINATION
        )
        if candidate
        else reference_loads
    )
    return adapter.ForecastFrame(
        focal_action=DESTINATION if candidate else SOURCE,
        nonfocal_actions=_reference_actions(),
        served_users=tuple(range(100)),
        active_beams=(SOURCE, DESTINATION, OTHER),
        active_satellites=(8, 9),
        loads=loads,
        r3_total=c3.canonical_r3_total(loads),
        power=_power(9.0 if candidate else 10.0),
        event=(c3.EventClass.PHI1 if candidate and interval == 0 else c3.EventClass.NONE),
        hold_valid=True,
        service=True,
    )


class FakeBackend:
    """A minimal backend contract fixture with no realised-outcome channel."""

    def __init__(
        self,
        *,
        same_branch: bool = False,
        mismatched_fingerprint: bool = False,
        wrong_equal_fingerprint: bool = False,
        asymmetric_rng_consumption: bool = False,
    ):
        self.same_branch = same_branch
        self.mismatched_fingerprint = mismatched_fingerprint
        self.wrong_equal_fingerprint = wrong_equal_fingerprint
        self.asymmetric_rng_consumption = asymmetric_rng_consumption
        self.calls: list[tuple[str, object]] = []
        self._shared = SimpleNamespace(label="shared")

    def replay_prefix(self, anchor: object) -> object:
        self.calls.append(("replay_prefix", anchor))
        if self.same_branch:
            return self._shared
        return SimpleNamespace(label=len(self.calls))

    def fingerprint(self, branch: object) -> str:
        self.calls.append(("fingerprint", branch))
        if self.wrong_equal_fingerprint:
            return WRONG_EQUAL_FINGERPRINT
        if self.mismatched_fingerprint and getattr(branch, "label", 0) > 1:
            return "b" * 64
        return ANCHOR_FINGERPRINT

    def roll_forward(
        self,
        branch: object,
        focal_physical_id: tuple[int, int],
        interval: int,
        forecast_rng: object,
    ) -> object:
        self.calls.append(("roll_forward", (branch, focal_physical_id, interval)))
        # Consumption is deliberate: reference/candidate streams are distinct
        # objects even though their domain-derived initial states are equal.
        forecast_rng.integers(0, 2**31)
        if self.asymmetric_rng_consumption and focal_physical_id == SOURCE:
            forecast_rng.integers(0, 2**31)
        return _frame(interval, candidate=focal_physical_id == DESTINATION)


def _anchor() -> object:
    return adapter.PreOutcomeAnchor(
        checkpoint_sha256=CHECKPOINT,
        expected_anchor_fingerprint_sha256=ANCHOR_FINGERPRINT,
        evaluation_seed=7,
        step_index=2,
        focal_user_id=0,
        source_id=SOURCE,
        prefix_actions=((1, 2, 3), (4, 5, 6)),
    )


def test_h3_adapter_replays_fresh_twins_and_builds_three_core_intervals():
    backend = FakeBackend()
    receipt = adapter.certify_h3_candidate(
        backend,
        anchor=_anchor(),
        candidate_id=DESTINATION,
    )

    assert receipt.status == "PASS"
    assert receipt.candidate_evidence is not None
    assert receipt.candidate_evidence.joint
    assert len(receipt.candidate_evidence.intervals) == 3
    assert receipt.anchor_fingerprint_sha256 == ANCHOR_FINGERPRINT
    assert receipt.forecast_rng_objects_distinct
    assert receipt.forecast_initial_state_sha256[0] == receipt.forecast_initial_state_sha256[1]
    assert len(receipt.forecast_final_state_sha256) == 2
    assert [kind for kind, _ in backend.calls[:4]] == [
        "replay_prefix",
        "replay_prefix",
        "fingerprint",
        "fingerprint",
    ]
    assert all(kind == "roll_forward" for kind, _ in backend.calls[4:])


def test_h3_adapter_domain_rng_is_repeatable_but_branch_objects_are_independent():
    first = adapter.certify_h3_candidate(
        FakeBackend(), anchor=_anchor(), candidate_id=DESTINATION
    )
    second = adapter.certify_h3_candidate(
        FakeBackend(), anchor=_anchor(), candidate_id=DESTINATION
    )

    assert first.status == second.status == "PASS"
    assert first.forecast_initial_state_sha256 == second.forecast_initial_state_sha256
    assert first.forecast_final_state_sha256 == second.forecast_final_state_sha256


def test_h3_adapter_fails_closed_when_replay_does_not_create_two_fresh_branches():
    backend = FakeBackend(same_branch=True)
    receipt = adapter.certify_h3_candidate(
        backend, anchor=_anchor(), candidate_id=DESTINATION
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert "fresh_branch_objects_not_distinct" in receipt.reasons
    assert not any(kind == "roll_forward" for kind, _ in backend.calls)


def test_h3_adapter_fails_closed_on_anchor_fingerprint_drift():
    backend = FakeBackend(mismatched_fingerprint=True)
    receipt = adapter.certify_h3_candidate(
        backend, anchor=_anchor(), candidate_id=DESTINATION
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert "anchor_fingerprint_mismatch" in receipt.reasons


def test_h3_adapter_fails_closed_on_wrong_but_equal_twin_fingerprints():
    """Equality alone must not authorize two identically wrong branches."""

    receipt = adapter.certify_h3_candidate(
        FakeBackend(wrong_equal_fingerprint=True),
        anchor=_anchor(),
        candidate_id=DESTINATION,
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert receipt.anchor_fingerprint_sha256 == WRONG_EQUAL_FINGERPRINT
    assert "anchor_fingerprint_not_bound_to_authority" in receipt.reasons


def test_h3_adapter_rejects_checkpoint_digest_as_anchor_state_authority():
    anchor = replace(
        _anchor(), expected_anchor_fingerprint_sha256=CHECKPOINT
    )
    receipt = adapter.certify_h3_candidate(
        FakeBackend(), anchor=anchor, candidate_id=DESTINATION
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert "checkpoint hash cannot be used as the anchor state fingerprint" in receipt.reasons[0]


def test_h3_adapter_fails_closed_on_asymmetric_forecast_rng_consumption():
    receipt = adapter.certify_h3_candidate(
        FakeBackend(asymmetric_rng_consumption=True),
        anchor=_anchor(),
        candidate_id=DESTINATION,
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert receipt.forecast_rng_objects_distinct
    assert receipt.forecast_initial_state_sha256[0] == receipt.forecast_initial_state_sha256[1]
    assert receipt.forecast_final_state_sha256[0] != receipt.forecast_final_state_sha256[1]
    assert "forecast_rng_state_mismatch_h0" in receipt.reasons


def test_h3_adapter_rejects_incomplete_nonfocal_evidence_before_certification():
    class IncompleteBackend(FakeBackend):
        def roll_forward(self, branch, focal_physical_id, interval, forecast_rng):
            frame = super().roll_forward(
                branch, focal_physical_id, interval, forecast_rng
            )
            actions = dict(frame.nonfocal_actions)
            actions.pop(99)
            return replace(frame, nonfocal_actions=actions)

    receipt = adapter.certify_h3_candidate(
        IncompleteBackend(), anchor=_anchor(), candidate_id=DESTINATION
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert any("nonfocal action map" in reason for reason in receipt.reasons)


def test_h3_adapter_keeps_power_identity_failures_as_core_evidence_not_silent_success():
    class BadPowerBackend(FakeBackend):
        def roll_forward(self, branch, focal_physical_id, interval, forecast_rng):
            frame = super().roll_forward(
                branch, focal_physical_id, interval, forecast_rng
            )
            if focal_physical_id == DESTINATION and interval == 1:
                return replace(frame, power=replace(frame.power, reported_system_power_w=99.0))
            return frame

    receipt = adapter.certify_h3_candidate(
        BadPowerBackend(), anchor=_anchor(), candidate_id=DESTINATION
    )

    assert receipt.status == "REJECT"
    assert receipt.candidate_evidence is not None
    assert not receipt.candidate_evidence.joint
    assert any("reported_system_power_mismatch" in reason for reason in receipt.reasons)


def test_h3_adapter_rejects_invalid_candidate_pair_without_backend_calls():
    backend = FakeBackend()
    receipt = adapter.certify_h3_candidate(
        backend, anchor=_anchor(), candidate_id=(9, 2)
    )

    assert receipt.status == "FAIL_CLOSED"
    assert receipt.candidate_evidence is None
    assert not backend.calls
    assert any("same satellite" in reason for reason in receipt.reasons)
