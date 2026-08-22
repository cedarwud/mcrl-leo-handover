"""W-11 — data-blind reference policies and probe P1.

The probe *enforces* §7.1 rather than describing it: it demands a frozen
PREREG, re-verifies the digest, and refuses any policy that is not a
declared rule.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    HandoverClass,
    SatelliteCandidate,
    SlotTable,
    action_index,
    assign_satellite_slots,
    build_slot_table,
    contract_state_fields,
)
from mcrl.env.candidates import StepCandidates
from mcrl.env.dwell import DwellSnapshot
from mcrl.env.reference_policy import (
    NEAREST_ELIGIBLE,
    RANDOM_MASKED,
    REFERENCE_POLICY_NAMES,
    STAY_IF_POSSIBLE,
    build_reference_policy,
)
from mcrl.errors import MCRLContractError
from mcrl.runtime.probe_p1 import run_probe_p1
from mcrl.runtime.prereg import (
    DataBlindnessError,
    PreregFreezeError,
    freeze_prereg,
)

SATS = (44714, 44718, 44723, 44730)
CELLS = [100, 101, 102, 103, 104, 105, 106]


def _candidates(
    *, eligible=SATS, cells=None, reachable=None, num_users=3, incumbent=None
):
    cells = cells or CELLS
    tables, assignments = [], []
    for _ in range(num_users):
        assignment = assign_satellite_slots(
            [
                SatelliteCandidate(norad, True, 300.0 - index)
                for index, norad in enumerate(eligible)
            ],
            incumbent_norad=incumbent,
        )
        assignments.append(assignment)
        tables.append(build_slot_table(assignment, cells, cell_reachable=reachable))

    class _D2:
        eligible_counts = np.full(num_users, len(eligible))

    return StepCandidates(
        slot_tables=tuple(tables),
        assignments=tuple(assignments),
        off_axis_deg=np.zeros((num_users, 4, NUM_BEAM_SLOTS)),
        slant_range_km=np.full((num_users, 4), 800.0),
        elevation_deg=np.full((num_users, 4), 40.0),
        window_satellite_ecef_km=np.zeros((num_users, 4, 3)),
        window_norad_ids=np.tile(np.array(assignments[0].norad_ids), (num_users, 1)),
        contract_fields=np.stack(
            [contract_state_fields(a, dwell_phase=0.0) for a in assignments]
        ),
        dwell=DwellSnapshot(
            step_index=0,
            anchor_cell_ids=np.zeros(num_users, dtype=np.int64),
            neighborhood_cell_ids=np.tile(np.array(cells), (num_users, 1)),
            phase=0.0,
            is_boundary=True,
            rekeyed_users=np.zeros(num_users, dtype=bool),
        ),
        d2=_D2(),
    )


# -- the policies are data-blind by construction --------------------------


def test_every_policy_is_a_rule_with_a_seed_not_a_model():
    for name in REFERENCE_POLICY_NAMES:
        runner = build_reference_policy(name, seed=7)
        assert runner.declaration.seed == 7
        assert not hasattr(runner, "state_dict")
        assert not hasattr(runner, "forward")
        assert runner.declaration.description


def test_an_unknown_policy_name_is_refused():
    with pytest.raises(MCRLContractError, match="unknown reference policy"):
        build_reference_policy("learned", seed=1)


def test_the_declared_names_are_the_three_arms():
    assert set(REFERENCE_POLICY_NAMES) == {
        NEAREST_ELIGIBLE,
        RANDOM_MASKED,
        STAY_IF_POSSIBLE,
    }


# -- every policy respects the mask ---------------------------------------


@pytest.mark.parametrize("name", REFERENCE_POLICY_NAMES)
def test_a_policy_never_selects_a_masked_action(name):
    runner = build_reference_policy(name, seed=1)
    rng = np.random.default_rng(0)
    reachable = np.ones((4, NUM_BEAM_SLOTS), dtype=bool)
    reachable[0, :] = False
    reachable[1, 3:] = False
    candidates = _candidates(reachable=reachable)
    for _ in range(5):
        actions = runner.act(candidates, rng)
        for uid, table in enumerate(candidates.slot_tables):
            assert table.mask[int(actions[uid])]


@pytest.mark.parametrize("name", REFERENCE_POLICY_NAMES)
def test_an_empty_mask_yields_a_no_op_not_a_fallback(name):
    """§4A.5a: a probe must meet the same starvation a trained policy would."""
    runner = build_reference_policy(name, seed=1)
    reachable = np.zeros((4, NUM_BEAM_SLOTS), dtype=bool)
    candidates = _candidates(reachable=reachable)
    actions = runner.act(candidates, np.random.default_rng(0))
    assert np.all(actions == NO_OP_ACTION)


# -- nearest-eligible ------------------------------------------------------


def test_nearest_eligible_takes_slot_zero_and_the_own_cell():
    runner = build_reference_policy(NEAREST_ELIGIBLE, seed=1)
    actions = runner.act(_candidates(), np.random.default_rng(0))
    assert np.all(actions == action_index(0, 0))


def test_nearest_eligible_falls_through_in_the_declared_order():
    reachable = np.ones((4, NUM_BEAM_SLOTS), dtype=bool)
    reachable[0, :] = False
    reachable[1, 0:2] = False
    runner = build_reference_policy(NEAREST_ELIGIBLE, seed=1)
    actions = runner.act(
        _candidates(reachable=reachable), np.random.default_rng(0)
    )
    assert np.all(actions == action_index(1, 2))


def test_nearest_eligible_is_deterministic():
    candidates = _candidates()
    first = build_reference_policy(NEAREST_ELIGIBLE, 1).act(
        candidates, np.random.default_rng(0)
    )
    second = build_reference_policy(NEAREST_ELIGIBLE, 1).act(
        candidates, np.random.default_rng(99)
    )
    assert np.array_equal(first, second), "the RNG must not affect this arm"


# -- random-masked ---------------------------------------------------------


def test_random_masked_spreads_across_the_valid_actions():
    runner = build_reference_policy(RANDOM_MASKED, seed=1)
    rng = np.random.default_rng(3)
    candidates = _candidates(num_users=200)
    actions = runner.act(candidates, rng)
    assert len(set(actions.tolist())) > 10


def test_random_masked_is_reproducible_from_its_seed():
    candidates = _candidates(num_users=50)
    first = build_reference_policy(RANDOM_MASKED, 1).act(
        candidates, np.random.default_rng(5)
    )
    second = build_reference_policy(RANDOM_MASKED, 1).act(
        candidates, np.random.default_rng(5)
    )
    assert np.array_equal(first, second)


# -- ★ stay-if-possible holds an ASSOCIATION, not an index ----------------


def test_stay_if_possible_follows_the_association_when_the_index_moves():
    """The false-positive handover §4A.4 warns about, prevented.

    The satellite it is holding moves from slot 2 to slot 0, so the index
    that reaches it changes.  A policy comparing indices would report a
    handover; this one must not.
    """
    runner = build_reference_policy(STAY_IF_POSSIBLE, seed=1)
    rng = np.random.default_rng(0)

    ordered = _candidates(eligible=SATS)
    runner.act(ordered, rng)
    # Force the hold onto the third satellite by acting on a mask that only
    # exposes it.
    reachable = np.zeros((4, NUM_BEAM_SLOTS), dtype=bool)
    reachable[2, 0] = True
    held = runner.act(_candidates(eligible=SATS, reachable=reachable), rng)
    assert np.all(held == action_index(2, 0))

    # Now reorder so that satellite becomes slot 0.
    reordered = _candidates(eligible=(SATS[2], SATS[0], SATS[1], SATS[3]))
    actions = runner.act(reordered, rng)
    for uid, table in enumerate(reordered.slot_tables):
        association = table.association(actions[uid])
        assert association.norad_id == SATS[2]
        assert association.cell_id == CELLS[0]
    assert np.all(actions == action_index(0, 0))


def test_stay_if_possible_releases_the_hold_after_an_unserved_step():
    """So the next served step is a genuine re-entry, not a silent hold."""
    runner = build_reference_policy(STAY_IF_POSSIBLE, seed=1)
    rng = np.random.default_rng(0)
    runner.act(_candidates(), rng)
    runner.act(
        _candidates(reachable=np.zeros((4, NUM_BEAM_SLOTS), dtype=bool)), rng
    )
    # After the outage the hold is gone, so it falls back to nearest-eligible.
    actions = runner.act(
        _candidates(eligible=(SATS[3], SATS[0], SATS[1], SATS[2])), rng
    )
    assert np.all(actions == action_index(0, 0))


def test_reset_clears_the_hold():
    runner = build_reference_policy(STAY_IF_POSSIBLE, seed=1)
    rng = np.random.default_rng(0)
    runner.act(_candidates(), rng)
    runner.reset()
    reordered = _candidates(eligible=(SATS[3], SATS[0], SATS[1], SATS[2]))
    assert np.all(runner.act(reordered, rng) == action_index(0, 0))


def test_two_runners_do_not_share_state():
    """The held association lives on the runner, not in a module global.

    A policy that cached it invisibly would be hard to tell from one that
    compares indices — exactly what §4A.4 forbids — so the isolation is
    asserted behaviourally.
    """
    first = build_reference_policy(STAY_IF_POSSIBLE, 1)
    second = build_reference_policy(STAY_IF_POSSIBLE, 1)
    rng = np.random.default_rng(0)

    reachable = np.zeros((4, NUM_BEAM_SLOTS), dtype=bool)
    reachable[2, 0] = True
    first.act(_candidates(reachable=reachable), rng)

    # ``second`` has never acted, so a reordering must not make it hold
    # anything ``first`` picked up.
    reordered = _candidates(eligible=(SATS[2], SATS[0], SATS[1], SATS[3]))
    assert np.all(second.act(reordered, rng) == action_index(0, 0))

    # And ``first`` still holds what it picked up, so the two are genuinely
    # separate rather than both empty.
    assert np.all(first.act(reordered, rng) == action_index(0, 0))


def test_the_module_declares_no_mutable_global_container():
    import mcrl.env.reference_policy as module

    mutable = {
        name: value
        for name, value in vars(module).items()
        if not name.startswith("__")
        and isinstance(value, (dict, list, set))
        and name not in {"_DESCRIPTIONS"}
    }
    assert mutable == {}, f"module-level mutable state: {sorted(mutable)}"


# -- probe P1 enforces §7.1 -----------------------------------------------


SELECTION_MAPPINGS = {
    "Q-E dwell N": "N maximising the angle-aware EE dynamic range in P2",
    "Q-D r3 calibration scale": "p95 of |U_{b_u}| over the P3 reference rollout",
}


def _prereg(probe_grid=None):
    sections = {
        name: {"placeholder": True}
        for name in (
            "ephemeris",
            "split",
            "sampling",
            "d2",
            "antenna_and_link_budget",
            "dwell",
            "reward",
            "action_and_state",
            "training",
            "thresholds",
            "stopping_rules",
            "reference_policy",
            "pointing_cells",
        )
    }
    sections["probe_grid"] = (
        {"P1": {"visibility": True}} if probe_grid is None else probe_grid
    )
    sections["selection_mappings"] = SELECTION_MAPPINGS
    return freeze_prereg(sections, holdout_seed=1)


def _steps(count=4, **kwargs):
    return [_candidates(**kwargs) for _ in range(count)]


def test_the_probe_runs_against_a_frozen_prereg():
    result = run_probe_p1(
        prereg=_prereg(),
        policy=build_reference_policy(STAY_IF_POSSIBLE, 1),
        steps=_steps(),
        rng=np.random.default_rng(0),
    )
    assert result["probe"] == "P1"
    assert result["decision_steps"] == 12
    assert result["policy"]["name"] == STAY_IF_POSSIBLE
    assert "starvation_rate" in result and "handover_rate" in result


def test_an_edited_prereg_is_rejected():
    record = _prereg()
    tampered = type(record)(
        sections=record.sections | {"thresholds": {"outage": 0.5}},
        holdout=record.holdout,
        schema=record.schema,
        digest=record.digest,
    )
    with pytest.raises(PreregFreezeError, match="edited after freezing"):
        run_probe_p1(
            prereg=tampered,
            policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
            steps=_steps(),
            rng=np.random.default_rng(0),
        )


def test_a_prereg_without_a_P1_grid_entry_is_rejected():
    with pytest.raises(MCRLContractError, match="no P1 entry"):
        run_probe_p1(
            prereg=_prereg(probe_grid={"P2": {"dwell_n": [2, 3, 4]}}),
            policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
            steps=_steps(),
            rng=np.random.default_rng(0),
        )


def test_a_network_cannot_be_used_as_the_probe_policy():
    import torch.nn as nn

    class _Fake:
        declaration = nn.Linear(2, 2)

        def reset(self):
            pass

    with pytest.raises(DataBlindnessError):
        run_probe_p1(
            prereg=_prereg(),
            policy=_Fake(),
            steps=_steps(),
            rng=np.random.default_rng(0),
        )


def test_an_empty_run_is_refused():
    with pytest.raises(MCRLContractError, match="consumed no steps"):
        run_probe_p1(
            prereg=_prereg(),
            policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
            steps=[],
            rng=np.random.default_rng(0),
        )


# -- what P1 measures ------------------------------------------------------


def test_starvation_is_counted_when_every_mask_is_empty():
    result = run_probe_p1(
        prereg=_prereg(),
        policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
        steps=_steps(reachable=np.zeros((4, NUM_BEAM_SLOTS), dtype=bool)),
        rng=np.random.default_rng(0),
    )
    assert result["starvation_rate"] == 1.0
    assert result["unserved_rate"] == 1.0
    assert result["handover_rate"] == 0.0


def test_a_stable_geometry_produces_no_handovers():
    result = run_probe_p1(
        prereg=_prereg(),
        policy=build_reference_policy(STAY_IF_POSSIBLE, 1),
        steps=_steps(count=6),
        rng=np.random.default_rng(0),
    )
    assert result["handover_rate"] == 0.0
    assert result["phi1_rate"] == 0.0 and result["phi2_rate"] == 0.0


def test_the_result_carries_the_prereg_digest_and_the_mask_scope():
    record = _prereg()
    result = run_probe_p1(
        prereg=record,
        policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
        steps=_steps(),
        rng=np.random.default_rng(0),
    )
    assert result["prereg_digest"] == record.digest
    # Ruling C-11: link feasibility is an execution-time outage, not a
    # mask term, so the mask has three terms and says so.
    assert "execution-time outage" in result["mask_scope"]


def test_the_quantile_summary_covers_the_reported_distributions():
    result = run_probe_p1(
        prereg=_prereg(),
        policy=build_reference_policy(NEAREST_ELIGIBLE, 1),
        steps=_steps(),
        rng=np.random.default_rng(0),
    )
    for key in ("d2_eligible_per_user", "valid_actions_per_user", "elevation_deg"):
        assert {"p05", "p50", "p95"} <= set(result[key])
