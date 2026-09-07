"""Deterministic tests for the C3 V3 candidate-support shadow seam."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("c3_reward_aligned_v3_shadow_runner.py")
spec = importlib.util.spec_from_file_location("c3_v3_shadow_runner", MODULE_PATH)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)

adapter = runner.adapter
c3 = runner.core


SOURCE = (7, 1)
DESTINATION = (7, 2)
ANCHOR_FP = "a" * 64
CHECKPOINT = "b" * 64
FOCAL_USER = 2
USERS = 4


def _evaluation(associations: list[tuple[int, int] | None], *, bits: float = 1000.0):
    from mcrl.env.link_budget import fixed_power_w, pa_efficiency, supply_power_w, system_power_w

    loads: dict[tuple[int, int], int] = {}
    for association in associations:
        if association is not None:
            loads[association] = loads.get(association, 0) + 1
    beam_ids = tuple(sorted(loads))
    beam_power = np.asarray(
        [
            1.0
            if beam == SOURCE and loads.get(SOURCE, 0) >= 3
            else 0.8
            if beam == SOURCE
            else 0.5
            for beam in beam_ids
        ],
        dtype=np.float64,
    )
    link_power = np.asarray(
        [
            float(beam_power[beam_ids.index(association)])
            if association is not None
            else 0.0
            for association in associations
        ],
        dtype=np.float64,
    )
    efficiencies = pa_efficiency(beam_power)
    supply = supply_power_w(beam_power, efficiencies)
    counts = np.asarray([len(beam_ids)], dtype=np.float64)
    fixed = fixed_power_w(counts)
    total = system_power_w(supply, counts)
    served = np.asarray([association is not None for association in associations], dtype=bool)
    serving_satellite = np.asarray(
        [association[0] if association is not None else -1 for association in associations],
        dtype=np.int64,
    )
    serving_cell = np.asarray(
        [association[1] if association is not None else -1 for association in associations],
        dtype=np.int64,
    )
    reward_matrix = np.zeros((USERS, 3), dtype=np.float64)
    for user, association in enumerate(associations):
        reward_matrix[user, 2] = 0.0 if association is None else -float(loads[association])
    return SimpleNamespace(
        radiating=SimpleNamespace(
            norad_ids=np.asarray([beam[0] for beam in beam_ids], dtype=np.int64),
            cell_ids=np.asarray([beam[1] for beam in beam_ids], dtype=np.int64),
            power_w=beam_power,
        ),
        resolution=SimpleNamespace(
            served=served,
            serving_satellite=serving_satellite,
            serving_cell=serving_cell,
            eligible_load_by_beam=loads,
            active_beams=beam_ids,
        ),
        link_power_w=link_power,
        fixed_power_w=fixed,
        system_power_w=total,
        reward_matrix=reward_matrix,
        useful_bits=bits,
    )


def _main_decision() -> adapter.ScalarizedMainDecision:
    return adapter.ScalarizedMainDecision(
        actions=(0, 0, 0, 1),
        physical_actions=(SOURCE, SOURCE, SOURCE, DESTINATION),
        objective_weights=adapter.OBJECTIVE_WEIGHTS,
        q_values=((1.0,),) * USERS,
        masks=((True,),) * USERS,
    )


@dataclass
class _Branch:
    kind: str
    offset: int = 0


class _Backend:
    """Four-user deterministic canonical backend with positive C3 support."""

    def __init__(self):
        self.replay_count = 0
        self.received_reference_scripts = []

    def replay_prefix(self, anchor):
        kind = "reference" if self.replay_count == 0 else "candidate"
        self.replay_count += 1
        return _Branch(kind)

    def fingerprint(self, branch):
        return ANCHOR_FP

    def scalarized_main_decision(self, branch):
        return _main_decision()

    def anchor_evaluation(self, branch, decision):
        return _evaluation([SOURCE, SOURCE, SOURCE, DESTINATION])

    def _step(
        self,
        branch,
        associations,
        offset,
        *,
        release=False,
        branch_main_nonfocal_actions=None,
    ):
        expected = branch.offset
        assert expected == offset
        branch.offset += 1
        events = [c3.EventClass.NONE] * USERS
        if branch.kind == "candidate" and not release and offset == 0:
            events[FOCAL_USER] = c3.EventClass.INTRA_SATELLITE
        if branch_main_nonfocal_actions is None:
            branch_main_nonfocal_actions = {
                user: associations[user]
                for user in range(USERS)
                if user != FOCAL_USER
            }
        return runner.ShadowStep(
            evaluation=_evaluation(associations),
            focal_action=associations[FOCAL_USER],
            nonfocal_actions={
                0: associations[0],
                1: associations[1],
                3: associations[3],
            },
            useful_bits=1000.0,
            reentry=(False,) * USERS,
            events=tuple(events),
            preview_commit_equal=True,
            scalarized_main_action=SOURCE if release else None,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )

    def force_focal(
        self,
        branch,
        focal_physical_id,
        offset,
        *,
        reference_nonfocal_actions=None,
    ):
        if branch.kind == "reference":
            associations = [SOURCE, SOURCE, SOURCE, DESTINATION]
        else:
            associations = [SOURCE, SOURCE, DESTINATION, DESTINATION]
        assert associations[FOCAL_USER] == focal_physical_id
        branch_main_nonfocal_actions = {
            user: associations[user]
            for user in range(USERS)
            if user != FOCAL_USER
        }
        if reference_nonfocal_actions is not None:
            self.received_reference_scripts.append(
                (branch.kind, offset, dict(reference_nonfocal_actions))
            )
            for user, physical_id in reference_nonfocal_actions.items():
                associations[user] = physical_id
        return self._step(
            branch,
            associations,
            offset,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )

    def release_to_main(
        self,
        branch,
        offset,
        *,
        reference_nonfocal_actions=None,
    ):
        associations = [SOURCE, SOURCE, SOURCE, DESTINATION]
        branch_main_nonfocal_actions = {
            user: associations[user]
            for user in range(USERS)
            if user != FOCAL_USER
        }
        if reference_nonfocal_actions is not None:
            self.received_reference_scripts.append(
                (branch.kind, offset, dict(reference_nonfocal_actions))
            )
            for user, physical_id in reference_nonfocal_actions.items():
                associations[user] = physical_id
        return self._step(
            branch,
            associations,
            offset,
            release=True,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )


class _BranchLocalMainDivergenceBackend(_Backend):
    """Candidate Main disagrees, while the executed reference script is safe."""

    def _step(
        self,
        branch,
        associations,
        offset,
        *,
        release=False,
        branch_main_nonfocal_actions=None,
    ):
        if branch.kind == "candidate":
            branch_main_nonfocal_actions = dict(branch_main_nonfocal_actions or {})
            # User 0 is non-focal and this physical action is valid in every
            # fixture table, but it is deliberately not the reference script.
            branch_main_nonfocal_actions[0] = DESTINATION
        return super()._step(
            branch,
            associations,
            offset,
            release=release,
            branch_main_nonfocal_actions=branch_main_nonfocal_actions,
        )


class _AnchorMainDivergenceBackend(_BranchLocalMainDivergenceBackend):
    """Candidate anchor Main differs only in a non-focal physical action."""

    def scalarized_main_decision(self, branch):
        decision = _main_decision()
        if branch.kind == "candidate":
            return adapter.ScalarizedMainDecision(
                actions=decision.actions,
                physical_actions=(DESTINATION, SOURCE, SOURCE, DESTINATION),
                objective_weights=decision.objective_weights,
                q_values=decision.q_values,
                masks=decision.masks,
            )
        return decision


def _anchor() -> runner.C3V3ShadowAnchor:
    return runner.C3V3ShadowAnchor(
        checkpoint_sha256=CHECKPOINT,
        expected_anchor_fingerprint_sha256=ANCHOR_FP,
        evaluation_seed=11,
        step_index=0,
        focal_user_id=FOCAL_USER,
        source_id=SOURCE,
        prefix_actions=(),
    )


def test_candidate_support_passes_with_complete_main_only_shadow_evidence():
    receipt = runner.certify_candidate_support(
        _Backend(), anchor=_anchor(), candidate_id=DESTINATION, expected_user_count=USERS
    )
    assert receipt.status == "PASS"
    assert receipt.certified
    assert receipt.first_failed_layer is None
    assert receipt.replayed_fresh_branches
    assert receipt.destination_active_without_focal
    assert len(receipt.intervals) == 4
    assert receipt.candidate_energy_j < receipt.reference_energy_j
    assert receipt.candidate_useful_bits == receipt.reference_useful_bits
    assert receipt.intervals[0].candidate_r3_total > receipt.intervals[0].reference_r3_total
    assert all(
        row.reference_executed_nonfocal_actions
        == row.candidate_executed_nonfocal_actions
        for row in receipt.intervals
    )
    payload = receipt.to_dict()
    assert payload["claim_ceiling"].startswith("development shadow only")
    assert payload["certificate"]["passed"] is True
    assert all(
        row["reference_executed_nonfocal_actions"]
        == row["candidate_executed_nonfocal_actions"]
        for row in payload["intervals"]
    )


def test_candidate_branch_local_main_nonfocal_divergence_is_diagnostic_only():
    backend = _BranchLocalMainDivergenceBackend()
    receipt = runner.certify_candidate_support(
        backend,
        anchor=_anchor(),
        candidate_id=DESTINATION,
        expected_user_count=USERS,
    )
    assert receipt.status == "PASS"
    assert receipt.certified
    assert receipt.reasons == ()
    assert len(receipt.main_nonfocal_diagnostics) == c3.CERTIFICATE_STEPS
    assert all(not row.branch_main_nonfocal_match for row in receipt.main_nonfocal_diagnostics)
    payload = receipt.to_dict()
    assert len(payload["main_nonfocal_diagnostics"]) == c3.CERTIFICATE_STEPS
    assert all(
        not row["branch_main_nonfocal_match"]
        for row in payload["main_nonfocal_diagnostics"]
    )
    assert [kind for kind, _, _ in backend.received_reference_scripts] == [
        "candidate",
        "candidate",
        "candidate",
        "candidate",
    ]
    assert all(
        actual == {0: SOURCE, 1: SOURCE, 3: DESTINATION}
        for _, _, actual in backend.received_reference_scripts
    )


def test_anchor_main_nonfocal_divergence_is_diagnostic_only():
    receipt = runner.certify_candidate_support(
        _AnchorMainDivergenceBackend(),
        anchor=_anchor(),
        candidate_id=DESTINATION,
        expected_user_count=USERS,
    )
    assert receipt.status == "PASS"
    assert receipt.certified
    assert receipt.main_nonfocal_diagnostics[0].offset == -1
    assert not receipt.main_nonfocal_diagnostics[0].branch_main_nonfocal_match


class _UnmappableScriptBackend(_Backend):
    def force_focal(
        self,
        branch,
        focal_physical_id,
        offset,
        *,
        reference_nonfocal_actions=None,
    ):
        if branch.kind == "candidate" and reference_nonfocal_actions is not None:
            raise RuntimeError(
                "reference nonfocal physical ID disappeared from current candidate table"
            )
        return super().force_focal(
            branch,
            focal_physical_id,
            offset,
            reference_nonfocal_actions=reference_nonfocal_actions,
        )


def test_unmappable_reference_nonfocal_script_fails_closed():
    receipt = runner.certify_candidate_support(
        _UnmappableScriptBackend(),
        anchor=_anchor(),
        candidate_id=DESTINATION,
        expected_user_count=USERS,
    )
    assert receipt.status == "FAIL_CLOSED"
    assert receipt.certificate is None
    assert any("disappeared from current candidate table" in reason for reason in receipt.reasons)


class _IgnoringReferenceScriptBackend(_Backend):
    """A backend that reports its local non-focal action instead of executing the script."""

    def force_focal(
        self,
        branch,
        focal_physical_id,
        offset,
        *,
        reference_nonfocal_actions=None,
    ):
        if branch.kind == "candidate" and reference_nonfocal_actions is not None:
            associations = [DESTINATION, SOURCE, DESTINATION, DESTINATION]
            assert associations[FOCAL_USER] == focal_physical_id
            return self._step(branch, associations, offset)
        return super().force_focal(
            branch,
            focal_physical_id,
            offset,
            reference_nonfocal_actions=reference_nonfocal_actions,
        )


def test_actual_executed_nonfocal_identity_remains_hard_safe_guard():
    receipt = runner.certify_candidate_support(
        _IgnoringReferenceScriptBackend(),
        anchor=_anchor(),
        candidate_id=DESTINATION,
        expected_user_count=USERS,
    )
    assert receipt.status == "REJECT"
    assert receipt.first_failed_layer == "hard_safe"
    assert receipt.first_failed_offset is None
    assert "nonfocal_physical_action_mismatch" in receipt.reasons


class _BadLoadBackend(_Backend):
    def force_focal(
        self,
        branch,
        focal_physical_id,
        offset,
        *,
        reference_nonfocal_actions=None,
    ):
        if offset == 1:
            # Both twins preserve all non-focal actions, service, active sets,
            # and physical focal IDs, but the source/destination gap is only
            # one.  This must be a semantic strict-load rejection, not a
            # post-hoc exception.
            if branch.kind == "reference":
                associations = [SOURCE, DESTINATION, SOURCE, None]
            else:
                associations = [SOURCE, DESTINATION, DESTINATION, None]
            assert associations[FOCAL_USER] == focal_physical_id
            return self._step(branch, associations, offset)
        return super().force_focal(
            branch,
            focal_physical_id,
            offset,
            reference_nonfocal_actions=reference_nonfocal_actions,
        )


def test_first_failure_receipt_reports_strict_load_offset():
    receipt = runner.certify_candidate_support(
        _BadLoadBackend(), anchor=_anchor(), candidate_id=DESTINATION, expected_user_count=USERS
    )
    assert receipt.status == "REJECT"
    assert not receipt.certified
    assert receipt.first_failed_layer == "strict_load"
    assert receipt.first_failed_offset == 1
    assert "strict_load_gap_failed" in receipt.reasons


class _SameBranchBackend(_Backend):
    def replay_prefix(self, anchor):
        if not hasattr(self, "branch"):
            self.branch = super().replay_prefix(anchor)
        return self.branch


def test_fresh_twin_failure_closes_without_certificate():
    receipt = runner.certify_candidate_support(
        _SameBranchBackend(), anchor=_anchor(), candidate_id=DESTINATION, expected_user_count=USERS
    )
    assert receipt.status == "FAIL_CLOSED"
    assert receipt.certificate is None
    assert receipt.reasons == ("fresh_deep_twin_objects_not_distinct",)


def test_unscheduled_anchor_is_composed_as_first_failure():
    receipt = runner.certify_candidate_support(
        _Backend(),
        anchor=_anchor(),
        candidate_id=DESTINATION,
        expected_user_count=USERS,
        scheduled_anchor=False,
    )
    assert receipt.status == "REJECT"
    assert receipt.first_failed_layer == "scheduled_anchor"
    assert receipt.first_failed_offset is None
    assert receipt.certificate is not None


def test_weight_drift_fails_closed_before_forecast():
    class BadWeights(_Backend):
        def scalarized_main_decision(self, branch):
            decision = _main_decision()
            return adapter.ScalarizedMainDecision(
                actions=decision.actions,
                physical_actions=decision.physical_actions,
                objective_weights=(1.0, 0.0, 0.0),
                q_values=decision.q_values,
                masks=decision.masks,
            )

    receipt = runner.certify_candidate_support(
        BadWeights(), anchor=_anchor(), candidate_id=DESTINATION, expected_user_count=USERS
    )
    assert receipt.status == "FAIL_CLOSED"
    assert "ValueError:Main decision weights" in receipt.reasons[0]
