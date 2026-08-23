"""W-07 / G-4 / G-12 — counting-form r3 and per-link feasibility.

B13 replaced ``r3`` with ``−U_{b_u}``, which made the reward depend on who
is *actually* served.  Ruling C-11 (2026-08-22) settled what does the
gating: the connection identity is two gates, ``x = a·z``, and the filter
between selecting and being served is **per-link power feasibility**, not a
second mask.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    SatelliteCandidate,
    action_index,
    assign_satellite_slots,
    build_slot_table,
)
from mcrl.env.link_budget import BEAM_BANDWIDTH_HZ
from mcrl.env.service import (
    R3_SCALE_IS_FROZEN,
    load_balance_identity,
    old_r3_is_load_blind,
    r3_counting,
    resolve_service,
    sample_r3_calibration,
)
from mcrl.errors import MCRLContractError

CELLS = [100, 101, 102, 103, 104, 105, 106]
SATS = (44714, 44718, 44723)


def _table(incumbent=None, cells=None):
    candidates = [
        SatelliteCandidate(norad_id=norad, eligible=True, margin_km=300.0 - index)
        for index, norad in enumerate(SATS)
    ]
    assignment = assign_satellite_slots(candidates, incumbent_norad=incumbent)
    return build_slot_table(assignment, cells or CELLS)


def _beam(slot=0, beam_slot=0):
    """The ``(norad_id, cell_id)`` key an action realises.

    ``resolve_service`` keys its two load dicts by BEAM, because (3.3) sums
    ``x_{u,s,v}`` for a fixed ``(s, v)``.  A cell id alone is not a beam:
    two satellites can illuminate one cell, and each carries its own load.
    """
    return (SATS[slot], CELLS[beam_slot])


def _resolve(actions, *, drop=(), users=None):
    """``drop`` names users whose chosen link is power-infeasible."""
    users = len(actions) if users is None else users
    tables = [_table() for _ in range(users)]
    infeasible = np.zeros(users, dtype=bool)
    for uid, _action in drop:
        infeasible[uid] = True
    return resolve_service(np.array(actions), tables, infeasible)


# -- the two load quantities ----------------------------------------------


def test_ungated_demand_and_eligible_load_are_reported_separately():
    """P-5/P-6: the state's load and the reward's load are different things."""
    a0 = action_index(0, 0)
    resolution = _resolve([a0, a0, a0], drop=[(2, a0)])

    assert resolution.demand_by_beam[_beam()] == 3, "state sees all three"
    assert resolution.eligible_load_by_beam[_beam()] == 2, "only two are served"
    assert resolution.served_count == 2
    assert resolution.outage_infeasible.tolist() == [False, False, True]


def test_an_infeasible_user_is_excluded_from_load_activation_and_reward():
    a0 = action_index(0, 0)
    resolution = _resolve([a0, a0], drop=[(1, a0)])
    loads = resolution.user_beam_load()
    assert loads.tolist() == [1.0, 0.0]
    assert r3_counting(resolution).tolist() == [-1.0, 0.0]
    assert resolution.serving_cell[1] == -1
    assert resolution.serving_satellite[1] == -1


def test_a_cell_whose_users_are_all_infeasible_is_not_active():
    """Activation ⟺ positive ELIGIBLE load, not positive demand (G-12)."""
    a0 = action_index(0, 0)
    resolution = _resolve([a0], drop=[(0, a0)])
    assert resolution.demand_by_beam[_beam()] == 1
    assert _beam() not in resolution.eligible_load_by_beam
    assert resolution.active_beams == ()


def test_no_op_users_contribute_to_neither_quantity():
    a0 = action_index(0, 0)
    resolution = _resolve([a0, NO_OP_ACTION])
    assert resolution.no_op_users.tolist() == [False, True]
    assert resolution.demand_by_beam == {_beam(): 1}
    assert resolution.eligible_load_by_beam == {_beam(): 1}
    assert not resolution.outage_infeasible.any(), "a no-op is not an infeasibility outage"


def test_a_no_op_is_distinguished_from_an_infeasibility_outage():
    """Different causes, different rates, so P1 can tell them apart."""
    a0 = action_index(0, 0)
    resolution = _resolve([NO_OP_ACTION, a0], drop=[(1, a0)])
    assert resolution.no_op_users.tolist() == [True, False]
    assert resolution.outage_infeasible.tolist() == [False, True]
    assert resolution.served_count == 0


def test_an_action_invalid_at_decision_time_is_a_contract_violation():
    """P-4 should have stopped it long before execution."""
    table = _table()
    masks = np.zeros(1, dtype=bool)
    dead = np.flatnonzero(~table.mask)
    if dead.size == 0:
        pytest.skip("this slot table has no invalid action")
    with pytest.raises(MCRLContractError, match="invalid at decision time"):
        resolve_service(np.array([dead[0]]), [table], masks)


def test_out_of_range_actions_are_refused():
    with pytest.raises(MCRLContractError, match="out of range"):
        resolve_service(np.array([NUM_ACTIONS]), [_table()], np.zeros(1, bool))


def test_shape_mismatches_fail_loud():
    with pytest.raises(MCRLContractError, match="link_infeasible"):
        resolve_service(np.array([0]), [_table()], np.ones(5, bool))
    with pytest.raises(MCRLContractError, match="one decision slot table"):
        resolve_service(np.array([0, 0]), [_table()], np.zeros(2, bool))


# -- G-4: r3 is decomposable ----------------------------------------------


def test_G4_r3_depends_only_on_the_users_own_beam_load():
    """No global scalar: a busier beam elsewhere must not move my reward."""
    a0, a1 = action_index(0, 0), action_index(0, 1)
    alone = _resolve([a0, a1])
    crowded = _resolve([a0, a1, a1, a1, a1])
    assert r3_counting(alone)[0] == r3_counting(crowded)[0] == -1.0
    # The users who piled onto the other beam feel it; user 0 does not.
    assert r3_counting(crowded)[1] == -4.0


def test_G4_r3_is_exactly_minus_the_beam_population():
    a0 = action_index(0, 0)
    for population in (1, 2, 5, 17):
        resolution = _resolve([a0] * population)
        assert r3_counting(resolution).tolist() == [-float(population)] * population


def test_G4_an_unserved_user_scores_zero_not_minus_one():
    resolution = _resolve([NO_OP_ACTION])
    assert r3_counting(resolution).tolist() == [0.0]


# -- the algebra B13 relies on --------------------------------------------


def test_the_sum_identity_holds():
    """``Σ_u U_{b_u} = Σ_b U_b²``."""
    actions = [action_index(0, j % 7) for j in range(20)]
    resolution = _resolve(actions)
    per_user, per_beam = load_balance_identity(resolution)
    assert per_user == per_beam


def test_an_even_spread_minimises_the_penalty():
    """Which is what makes maximising Σ r3 load balancing."""
    even = _resolve([action_index(0, j) for j in range(7)] * 2)
    lumped = _resolve([action_index(0, 0)] * 14)
    assert abs(r3_counting(even).sum()) < abs(r3_counting(lumped).sum())
    assert load_balance_identity(even)[1] == 7 * 2**2
    assert load_balance_identity(lumped)[1] == 14**2


def test_the_degenerate_case_is_min_max_balancing():
    """With empty beams present the gap is ``max U_{s,v}``."""
    resolution = _resolve([action_index(0, 0)] * 3 + [action_index(0, 1)])
    loads = resolution.user_beam_load()
    assert loads.max() == 3.0
    assert max(resolution.eligible_load_by_beam.values()) == 3


def test_the_old_form_really_was_load_blind():
    """B13's premise, demonstrated rather than asserted."""
    assert old_r3_is_load_blind([1, 2, 5, 20])


# -- gamma_req is GONE (PATCH P-22) ---------------------------------------
#
# ``required_sinr()`` had zero live consumers, cited a legacy-only ``R^m``
# (ruling C-12, whose active contract "明文排除最低速率反推"), and was the
# first half of the target-SINR inversion ruling C-2 forbids outright.  The
# five tests that exercised it went with it -- a test suite for a deleted
# surface is what keeps a deleted surface alive.







# -- Q-D stays open -------------------------------------------------------


def test_the_r3_scale_is_frozen_at_what_probe_p3_measured():
    """Q-D closed 2026-08-23 — by a probe, which is what the flag was for.

    B13 changed r3's units from a normalised gap to a raw head count, so the
    inherited scale meant nothing and the flag held training back until a
    measurement existed.  P3 supplied it: p95 of |r3| over served steps,
    rounded, per the mapping frozen BEFORE the probe ran.
    """
    from mcrl.env.service import R3_CALIBRATION_SCALE

    assert R3_SCALE_IS_FROZEN is True
    assert R3_CALIBRATION_SCALE == 6


def test_calibration_sampling_reports_statistics_not_a_scale():
    """Choosing a scale from data the probe has seen is the §7.1 leak."""
    resolution = _resolve([action_index(0, 0)] * 3 + [action_index(0, 1)])
    sample = sample_r3_calibration(resolution)
    assert sample.served == 4
    assert sample.max_abs_r3 == 3.0
    assert sample.spread == 2.0
    assert not hasattr(sample, "scale")


def test_calibration_sampling_survives_an_all_unserved_step():
    sample = sample_r3_calibration(_resolve([NO_OP_ACTION, NO_OP_ACTION]))
    assert sample.served == 0
    assert sample.mean_abs_r3 == 0.0
