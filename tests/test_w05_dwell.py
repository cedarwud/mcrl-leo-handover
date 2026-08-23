"""W-05 — earth-fixed dwell and cell re-keying (SDD §3.4, §4A.2, T6)."""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.env.action_contract import (
    HandoverClass,
    HandoverLedger,
    SatelliteCandidate,
    action_index,
    assign_satellite_slots,
    build_slot_table,
)
from mcrl.env.cells import build_cell_grid
from mcrl.env.dwell import (
    DWELL_N_CANDIDATES,
    DwellConfig,
    DwellController,
    segments_per_service_window,
)
from mcrl.errors import MCRLContractError

MEASURED_ALTITUDE_KM = 485.0
SERVICE_WINDOW_10DEG_S = 378.0
"""docs/EPHEMERIS-NOTES.md §7 — pass duration p50 above 10°, 6.3 min."""

HORIZON_WINDOW_S = 630.0
"""The 10.5 min horizon-to-horizon figure — explicitly NOT the one to use."""


@pytest.fixture(scope="module")
def grid():
    return build_cell_grid(altitude_km=MEASURED_ALTITUDE_KM)


def _controller(grid, users=3, steps=3):
    return DwellController(grid, users, DwellConfig(steps=steps))


def _positions(users=3):
    return np.array([[0.0, 0.0], [30.0, 10.0], [-40.0, -20.0]][:users])


# -- segment structure -----------------------------------------------------


def test_boundaries_fall_every_N_steps():
    config = DwellConfig(steps=3)
    boundaries = [step for step in range(12) if config.is_boundary(step)]
    assert boundaries == [0, 3, 6, 9]


def test_phase_is_normalised_so_a_swept_N_does_not_change_its_range():
    """P2 sweeps N; a feature whose scale moves with N would confound it."""
    for steps in DWELL_N_CANDIDATES:
        config = DwellConfig(steps=steps)
        phases = [config.phase(step) for step in range(steps * 3)]
        assert min(phases) == 0.0
        assert max(phases) < 1.0
        assert phases[0] == 0.0
        assert len(set(phases)) == steps


def test_phase_is_zero_exactly_on_boundaries():
    config = DwellConfig(steps=4)
    for step in range(20):
        assert (config.phase(step) == 0.0) == config.is_boundary(step)


def test_a_zero_length_dwell_is_refused():
    with pytest.raises(ValueError):
        DwellConfig(steps=0)


# -- the mapping is frozen between boundaries -----------------------------


def test_the_anchor_does_not_move_between_boundaries(grid):
    controller = _controller(grid)
    positions = _positions()
    first = controller.step(0, positions)

    # Teleport the users far away mid-segment: earth-fixed means earth-fixed.
    moved = positions + np.array([60.0, 0.0])
    mid = controller.step(1, moved)
    assert np.array_equal(mid.anchor_cell_ids, first.anchor_cell_ids)
    assert mid.rekey_count == 0
    assert not mid.is_boundary

    # At the next boundary it catches up.
    rekeyed = controller.step(3, moved)
    assert rekeyed.is_boundary
    assert not np.array_equal(rekeyed.anchor_cell_ids, first.anchor_cell_ids)
    assert rekeyed.rekey_count == len(positions)


def test_a_boundary_with_no_movement_rekeys_nobody(grid):
    controller = _controller(grid)
    positions = _positions()
    controller.step(0, positions)
    controller.step(1, positions)
    boundary = controller.step(3, positions)
    assert boundary.is_boundary
    assert boundary.rekey_count == 0


def test_realistic_user_motion_almost_never_moves_the_anchor(grid):
    """30 km/h for 10 s is 83 m against a ~14 km cell radius (§4A.2)."""
    controller = _controller(grid)
    positions = _positions()
    controller.step(0, positions)
    drift_km = 30.0 / 3600.0 * 10.0
    assert drift_km < 0.01 * grid.cell_radius_km
    drifted = positions + np.array([drift_km, 0.0])
    assert controller.step(3, drifted).rekey_count == 0


def test_the_neighbourhood_follows_the_anchor(grid):
    controller = _controller(grid)
    snapshot = controller.step(0, _positions())
    assert snapshot.neighborhood_cell_ids.shape == (3, 7)
    assert np.array_equal(
        snapshot.neighborhood_cell_ids[:, 0], snapshot.anchor_cell_ids
    )


def test_a_segment_must_start_on_a_boundary(grid):
    controller = _controller(grid)
    with pytest.raises(MCRLContractError, match="must be a dwell boundary"):
        controller.step(1, _positions())


def test_reset_forces_a_fresh_boundary(grid):
    controller = _controller(grid)
    controller.step(0, _positions())
    controller.reset()
    with pytest.raises(MCRLContractError, match="not been stepped"):
        _ = controller.anchors
    with pytest.raises(MCRLContractError, match="must be a dwell boundary"):
        controller.step(2, _positions())


def test_misshaped_positions_fail_loud(grid):
    controller = _controller(grid)
    with pytest.raises(MCRLContractError, match="shape"):
        controller.step(0, np.zeros((2, 2)))


# -- T6: a re-key under a fixed index is a phi1 ---------------------------


def test_T6_a_rekey_that_moves_cell_zero_is_charged_as_phi1(grid):
    """The whole reason the ledger reads cells, not indices (§4A.7 T6)."""
    controller = _controller(grid, users=1)
    candidate = SatelliteCandidate(norad_id=44714, eligible=True, margin_km=300.0)
    ledger = HandoverLedger()

    start = np.array([[0.0, 0.0]])
    before = controller.step(0, start)
    assignment = assign_satellite_slots([candidate], incumbent_norad=None)
    table = build_slot_table(assignment, before.neighborhood_cell_ids[0])
    action = action_index(0, 0)
    assert ledger.observe(table.association(action)) is HandoverClass.NONE

    # Move far enough that the boundary re-anchors onto a different cell.
    moved = start + np.array([[60.0, 0.0]])
    after = controller.step(3, moved)
    assert after.rekey_count == 1
    later_table = build_slot_table(
        assign_satellite_slots([candidate], incumbent_norad=44714),
        after.neighborhood_cell_ids[0],
    )

    # Same satellite, same action index, different physical cell.
    assert later_table.association(action).norad_id == table.association(action).norad_id
    assert later_table.association(action).cell_id != table.association(action).cell_id
    assert ledger.observe(later_table.association(action)) is (
        HandoverClass.INTRA_SATELLITE
    )


def test_a_boundary_without_a_rekey_costs_nothing(grid):
    controller = _controller(grid, users=1)
    candidate = SatelliteCandidate(norad_id=44714, eligible=True, margin_km=300.0)
    ledger = HandoverLedger()
    positions = np.array([[0.0, 0.0]])

    for step in (0, 3):
        snapshot = controller.step(step, positions)
        table = build_slot_table(
            assign_satellite_slots([candidate], incumbent_norad=44714),
            snapshot.neighborhood_cell_ids[0],
        )
        result = ledger.observe(table.association(action_index(0, 0)))
    assert result is HandoverClass.NONE


# -- Q-E feasibility: which window the argument uses ----------------------


def test_segments_per_window_uses_the_ten_degree_figure():
    """Author ruling: the ≥10° window, not horizon-to-horizon."""
    for steps in DWELL_N_CANDIDATES:
        config = DwellConfig(steps=steps)
        usable = segments_per_service_window(
            config, service_window_s=SERVICE_WINDOW_10DEG_S
        )
        optimistic = segments_per_service_window(
            config, service_window_s=HORIZON_WINDOW_S
        )
        assert usable == pytest.approx(SERVICE_WINDOW_10DEG_S / steps)
        # Using the wrong window overstates the segment count by 1.67x.
        assert optimistic / usable == pytest.approx(HORIZON_WINDOW_S / SERVICE_WINDOW_10DEG_S)
        assert optimistic / usable == pytest.approx(1.667, abs=0.01)


def test_every_candidate_N_is_short_against_the_service_window():
    """A dwell segment must be brief next to the window, or the earth-fixed
    beam outlives the geometry that justified it."""
    for steps in DWELL_N_CANDIDATES:
        segments = segments_per_service_window(
            DwellConfig(steps=steps), service_window_s=SERVICE_WINDOW_10DEG_S
        )
        assert segments > 90.0, (steps, segments)


def test_the_sweep_is_the_one_the_spec_names():
    assert DWELL_N_CANDIDATES == (2, 3, 4)


def test_N_is_frozen_and_the_frozen_value_is_the_one_the_rule_returns():
    """Q-E closed on 2026-08-23 — and NOT by inertia, which is the point.

    ``N = 3`` was the sweep's midpoint and a declared placeholder for weeks,
    so "it was already there" is exactly the failure mode this guards. What
    changed is not the number but its provenance: the frozen mapping is
    "largest N with a re-key rate at or under 5%", and the measured rates at
    the frozen decision step are 2.7% / 3.8% / 5.4% for N = 2 / 3 / 4 — so
    the rule returns 3 on its own terms.

    The rule is deliberately independent of EE, throughput and every
    reported metric: SDD 4A.2 gives dwell one job (freeze ``j -> cell_id``
    so an index keeps naming one cell, which larger N serves better) and
    staleness is its only cost, which the re-key rate measures directly.
    """
    from mcrl.env.dwell import DWELL_N_IS_FROZEN
    from mcrl.runtime.prereg_draft import SELECTION_MAPPINGS

    assert DwellConfig().steps in DWELL_N_CANDIDATES
    assert DWELL_N_IS_FROZEN is True

    mapping = SELECTION_MAPPINGS["Q-E dwell N"]
    rates = mapping["measured_rekey_rate"][
        "authoritative_probe_P2_100_users_separated_streams"
    ]
    largest_under_bound = max(
        n for n in DWELL_N_CANDIDATES if rates[f"N={n}"] <= 0.05
    )
    assert largest_under_bound == DwellConfig().steps == mapping["resolved"] == 4


def test_the_dwell_mapping_freezes_its_measurement_conditions():
    """A rule without its conditions is not a rule (ruling W-28 §1).

    Q-E is the proof: the same wording selected 3 from a 60-user
    single-stream script and 4 from probe P2 at 100 users with separated
    streams.  Both measurements stay on the record with the reason they
    differ, so re-running P2 and getting a different N than an older note
    says does not read as a records error.
    """
    from mcrl.runtime.prereg_draft import SELECTION_MAPPINGS

    mapping = SELECTION_MAPPINGS["Q-E dwell N"]
    conditions = mapping["measurement_conditions"]
    assert "100 users" in conditions and "rng_policy" in conditions
    measured = mapping["measured_rekey_rate"]
    assert "authoritative_probe_P2_100_users_separated_streams" in measured
    assert "superseded_qe_rekey_script_60_users_single_stream" in measured
    assert "conditions, not sampling noise" in measured["why_they_differ"]


def test_the_sensitivity_record_does_not_claim_N_is_inconsequential():
    """It moves the P^N swing by 5.4%; only the handover rate is identical.

    Writing "no measurable effect" would make a later reader comparing the
    numbers think the record was wrong.
    """
    from mcrl.runtime.prereg_draft import SELECTION_MAPPINGS

    sensitivity = SELECTION_MAPPINGS["Q-E dwell N"]["p2_sensitivity_at_the_chosen_N"]
    swing = sensitivity["system_power_swing_w"]
    assert swing["N=4"] < swing["N=2"], "the swing does differ across N"
    assert len(set(sensitivity["handover_rate_per_decision"].values())) == 1
    assert "NOT 'no measurable effect'" in sensitivity["note"]


def test_a_full_episode_of_ten_steps_spans_several_segments(grid):
    """H = 10 with N = 3 means 4 boundaries inside one episode."""
    controller = _controller(grid, users=1)
    positions = np.array([[0.0, 0.0]])
    boundaries = 0
    for step in range(10):
        if controller.step(step, positions).is_boundary:
            boundaries += 1
    assert boundaries == 4
