from __future__ import annotations

import inspect
import sys
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_oracle_gate as v1  # noqa: E402
import run_state_observable_gate as gate  # noqa: E402
from mcrl.env.action_contract import NUM_ACTIONS  # noqa: E402


def _choice(
    action: int,
    key: tuple[int, int],
    *,
    load: float,
    sinr: float,
) -> v1.CandidateChoice:
    return v1.CandidateChoice(
        action=action,
        key=key,
        prior_demand=load,
        candidate_sinr=sinr,
        q1=float(action),
    )


def _access(action: int | None) -> np.ndarray:
    access = np.zeros(NUM_ACTIONS, dtype=np.float64)
    if action is not None:
        access[action] = 1.0
    return access


def test_proposal_api_has_no_other_user_or_outcome_input() -> None:
    parameters = set(inspect.signature(gate.state_only_proposal).parameters)

    assert parameters == {
        "family",
        "baseline_action",
        "baseline_key",
        "candidates",
        "access_vector",
    }


def test_r2_exact_stay_uses_only_visible_incumbent() -> None:
    candidates = [
        _choice(0, (20, 1), load=4.0, sinr=9.0),
        _choice(1, (10, 1), load=2.0, sinr=3.0),
    ]

    proposal = gate.state_only_proposal(
        gate.R2_FAMILY,
        baseline_action=0,
        baseline_key=(20, 1),
        candidates=candidates,
        access_vector=_access(1),
    )
    invisible = gate.state_only_proposal(
        gate.R2_FAMILY,
        baseline_action=0,
        baseline_key=(20, 1),
        candidates=candidates,
        access_vector=_access(None),
    )
    no_op = gate.state_only_proposal(
        gate.R2_FAMILY,
        baseline_action=1,
        baseline_key=(10, 1),
        candidates=candidates,
        access_vector=_access(1),
    )

    assert proposal.reason == "eligible"
    assert proposal.choice is not None and proposal.choice.action == 1
    assert invisible.reason == "incumbent_not_visible" and invisible.choice is None
    assert no_op.reason == "reference_already_exact_stay" and no_op.choice is None


def test_r2_rejects_ambiguous_visible_incumbent() -> None:
    access = _access(0)
    access[1] = 1.0

    with pytest.raises(RuntimeError, match="more than one incumbent"):
        gate.state_only_proposal(
            gate.R2_FAMILY,
            baseline_action=0,
            baseline_key=(20, 1),
            candidates=[
                _choice(0, (20, 1), load=1.0, sinr=1.0),
                _choice(1, (10, 1), load=1.0, sinr=1.0),
            ],
            access_vector=access,
        )


def test_prev_inactive_split_uses_sinr_then_action_tie_break() -> None:
    candidates = [
        _choice(0, (10, 1), load=5.0, sinr=20.0),
        _choice(1, (20, 1), load=0.0, sinr=7.0),
        _choice(2, (30, 1), load=0.0, sinr=7.0),
        _choice(3, (40, 1), load=1.0, sinr=99.0),
    ]

    proposal = gate.state_only_proposal(
        "r3_prev_inactive_split",
        baseline_action=0,
        baseline_key=(10, 1),
        candidates=candidates,
        access_vector=_access(None),
    )

    assert proposal.choice is not None and proposal.choice.action == 1
    assert [row[0] for row in proposal.selection_candidates] == [0, 1, 2, 3]


def test_prev_active_lower_load_uses_load_sinr_action_order() -> None:
    candidates = [
        _choice(0, (10, 1), load=5.0, sinr=20.0),
        _choice(1, (20, 1), load=2.0, sinr=99.0),
        _choice(2, (30, 1), load=1.0, sinr=3.0),
        _choice(3, (40, 1), load=1.0, sinr=8.0),
        _choice(4, (50, 1), load=0.0, sinr=100.0),
    ]

    proposal = gate.state_only_proposal(
        "r3_prev_active_lower_load",
        baseline_action=0,
        baseline_key=(10, 1),
        candidates=candidates,
        access_vector=_access(None),
    )

    assert proposal.choice is not None and proposal.choice.action == 3
    assert proposal.reference_prior_demand == 5.0


def test_prev_active_lower_load_requires_physical_reference() -> None:
    proposal = gate.state_only_proposal(
        "r3_prev_active_lower_load",
        baseline_action=-1,
        baseline_key=None,
        candidates=[_choice(1, (20, 1), load=1.0, sinr=7.0)],
        access_vector=_access(None),
    )

    assert proposal.choice is None
    assert proposal.reason == "reference_has_no_physical_candidate"


def test_split_topology_requires_true_net_plus_one_opening() -> None:
    base = {
        "realised_active_beams_added": [[20, 1]],
        "realised_proposed_beam_opening": True,
        "reference_effective_beams": 10,
        "alternative_effective_beams": 11,
        "delta_load_relief": 3.0,
    }

    assert gate.r3_role_labels("r3_prev_inactive_split", base) == {
        "load_endpoint_positive": True,
        "topology_endpoint_positive": True,
        "role_positive": True,
    }
    assert gate.r3_role_labels(
        "r3_prev_inactive_split", base | {"alternative_effective_beams": 10}
    )["role_positive"] is False
    assert gate.r3_role_labels(
        "r3_prev_inactive_split", base | {"realised_proposed_beam_opening": False}
    )["role_positive"] is False


def test_reuse_topology_requires_no_added_beam() -> None:
    reuse = {
        "realised_active_beams_added": [],
        "realised_proposed_beam_opening": False,
        "reference_effective_beams": 10,
        "alternative_effective_beams": 9,
        "delta_load_relief": 2.0,
    }

    assert gate.r3_role_labels("r3_prev_active_lower_load", reuse)[
        "role_positive"
    ] is True
    assert gate.r3_role_labels(
        "r3_prev_active_lower_load",
        reuse | {"realised_active_beams_added": [[20, 1]]},
    )["role_positive"] is False
    assert gate.r3_role_labels(
        "r3_prev_active_lower_load", reuse | {"delta_load_relief": 0.0}
    )["role_positive"] is False
