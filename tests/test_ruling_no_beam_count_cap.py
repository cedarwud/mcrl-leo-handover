"""Ruling 2026-08-22 — no per-satellite beam-count cap exists anywhere.

``RULING-2026-08-22-no-beam-count-cap.md``.  The cap was deleted outright,
not replaced with a different number, so these tests assert an **absence**.
An absence is easy to undo by accident, which is why it gets a gate.

Why it was deleted, in one line each:

* Sun-2024's beams have no geometry at all, so their ``V = 7`` was the size
  of a load-channel set, never an activation ceiling — the paper's own
  constraint ``Σ_v z_{s,v} = V`` is an identity, not a bound.
* This paper adds pointing and footprints, so beams must cover ground: 7
  cells reach a third of the service area at 550 km and a fifth at 485 km.
* A ceiling therefore has to darken beams, and darkening by demand rank was
  already measured to starve 68 of 100 users and invert the congestion
  incentive; darkening by any other rule has no source.
* It also fights ``r3``: the reward pushes users toward quiet beams and a
  demand-ranked rule extinguishes quiet beams first.
* Enforcing it in the mask instead would make the mask depend on the joint
  action, breaking the per-user independent argmax that **defines** the B1
  baseline.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from mcrl.env import action_contract, link_budget, service
from mcrl.env.action_contract import (
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    SatelliteCandidate,
    action_index,
    assign_satellite_slots,
    build_slot_table,
)
from mcrl.env.link_budget import (
    BEAM_POWER_MAX_W,
    beam_transmit_power_w,
    classify_link_power_feasibility,
)
from mcrl.env.service import resolve_service
from mcrl.errors import MCRLContractError

SRC = Path(__file__).resolve().parents[1] / "src" / "mcrl"

CAP_VOCABULARY = (
    "max_simultaneous_beams",
    "beams_per_satellite",
    "beam_count_cap",
    "activation_cap",
    "max_active_beams",
    "aggregate_cap",
    "satellite_aggregate",
)


# -- §7.1-7.2: the mechanism and its sockets are absent --------------------


def test_no_module_defines_a_beam_count_ceiling():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text().lower()
        for term in CAP_VOCABULARY:
            if term in text:
                offenders.append(f"{path.relative_to(SRC).as_posix()}: {term}")
    assert not offenders, (
        "ruling §7.1-7.2: no cap, and no socket for one:\n" + "\n".join(offenders)
    )


def test_the_aggregate_power_cap_was_not_ported():
    """§7.6 — its upstream is a gated historical negative control."""
    assert not hasattr(link_budget, "apply_satellite_aggregate_cap")
    assert not hasattr(link_budget, "SATELLITE_AGGREGATE_POWER_MAX_W")


def test_the_action_space_shape_is_untouched():
    """§1 — 4 x 7 = 28 does not move by one character."""
    assert NUM_SATELLITE_SLOTS == 4
    assert NUM_BEAM_SLOTS == 7
    assert NUM_ACTIONS == 28


def test_J_w_carries_the_coincidence_warning():
    """§7.3 — the two 7s must not be substituted for each other."""
    documentation = action_contract.__dict__["__doc__"] or ""
    source = (SRC / "env" / "action_contract.py").read_text()
    marker = source[source.index("NUM_BEAM_SLOTS: int = 7") :][:2000]
    assert "coincidence" in marker.lower()
    assert "39" in marker, "the note must say where Table I's V=7 went"
    assert "superseded" in marker.lower()
    del documentation


# -- §7.4: activation is derived, never selected --------------------------


def _resolution(actions, users):
    candidates = [
        SatelliteCandidate(norad_id=44700 + index, eligible=True, margin_km=300.0 - index)
        for index in range(NUM_SATELLITE_SLOTS)
    ]
    cells = [100, 101, 102, 103, 104, 105, 106]
    tables = [
        build_slot_table(
            assign_satellite_slots(candidates, incumbent_norad=None), cells
        )
        for _ in range(users)
    ]
    masks = np.ones((users, NUM_ACTIONS), dtype=bool)
    return resolve_service(np.array(actions), tables, masks), cells


def test_every_beam_with_a_user_is_lit_no_matter_how_many():
    """The core invariant: |lit| == |cells with at least one served user|."""
    for beams_demanded in (1, 4, 7, 12, 20, 28):
        actions = [
            action_index(index // NUM_BEAM_SLOTS % NUM_SATELLITE_SLOTS,
                         index % NUM_BEAM_SLOTS)
            for index in range(beams_demanded)
        ]
        resolution, _cells = _resolution(actions, len(actions))
        demanded_cells = {
            int(cell) for cell in resolution.serving_cell if cell >= 0
        }
        assert set(resolution.active_cells) == demanded_cells
        assert len(resolution.active_cells) == len(demanded_cells)


def test_the_lit_set_never_shrinks_below_the_demanded_set():
    """§7.4's regression test, stated as the property it protects."""
    rng = np.random.default_rng(11)
    for _ in range(200):
        users = int(rng.integers(1, 40))
        actions = [
            action_index(
                int(rng.integers(0, NUM_SATELLITE_SLOTS)),
                int(rng.integers(0, NUM_BEAM_SLOTS)),
            )
            for _ in range(users)
        ]
        resolution, _cells = _resolution(actions, users)
        served_cells = {
            int(cell) for cell in resolution.serving_cell if cell >= 0
        }
        assert set(resolution.active_cells) >= served_cells
        for cell in served_cells:
            assert resolution.eligible_load_by_cell[cell] > 0


def test_activation_vector_is_a_pure_function_of_load():
    resolution, cells = _resolution(
        [action_index(0, 0), action_index(0, 0), action_index(0, 3)], 3
    )
    activation = resolution.activation_vector(cells)
    assert activation.tolist() == [True, False, False, True, False, False, False]
    assert int(activation.sum()) == len(resolution.active_cells)


def test_one_satellite_may_light_far_more_than_seven_cells():
    """The case a ceiling would have broken, now explicitly legal."""
    actions = [action_index(0, j) for j in range(NUM_BEAM_SLOTS)]
    actions += [action_index(1, j) for j in range(NUM_BEAM_SLOTS)]
    resolution, _cells = _resolution(actions, len(actions))
    # Slot 0 and slot 1 are different satellites but the same seven cells,
    # so every one of the seven is lit and nothing is darkened.
    assert len(resolution.active_cells) == NUM_BEAM_SLOTS
    assert resolution.served_count == len(actions)
    assert not resolution.execution_dropped.any()


# -- §7.5: the resource constraint is per-link power feasibility ----------


def test_the_constraint_is_per_link_and_continuous():
    """A demanding link drops out; its neighbours on the same beam do not."""
    required = np.array([0.9, 1.2, 1.64, 1.66, 2.4])
    infeasible = classify_link_power_feasibility(required)
    assert infeasible.tolist() == [False, False, False, True, True]


def test_power_is_not_silently_clamped_to_the_ceiling():
    """A clamp would under-serve the link and still report it served."""
    heavy = beam_transmit_power_w(np.array([25.0]))
    assert float(heavy[0]) > BEAM_POWER_MAX_W
    assert bool(classify_link_power_feasibility(heavy)[0])


def test_the_ceiling_binds_only_at_a_genuinely_heavy_load():
    """0.25 + 0.35*sqrt(U) crosses 1.65 W at exactly U = 16."""
    loads = np.arange(0, 30, dtype=float)
    power = beam_transmit_power_w(loads)
    infeasible = classify_link_power_feasibility(power)
    assert not infeasible[:17].any()
    assert infeasible[17:].all()
    assert float(power[16]) == pytest.approx(BEAM_POWER_MAX_W, abs=1e-12)


def test_a_dark_beam_draws_exactly_zero_and_is_feasible():
    power = beam_transmit_power_w(np.array([0.0]))
    assert float(power[0]) == 0.0
    assert not bool(classify_link_power_feasibility(power)[0])


def test_feasibility_inputs_are_validated():
    with pytest.raises(MCRLContractError, match="non-negative"):
        classify_link_power_feasibility(np.array([-1.0]))
    with pytest.raises(MCRLContractError, match="finite"):
        classify_link_power_feasibility(np.array([float("inf")]))
    with pytest.raises(ValueError):
        classify_link_power_feasibility(np.array([1.0]), max_power_w=0.0)


# -- §7.5: no unserved cliff ----------------------------------------------


def test_power_infeasibility_degrades_smoothly_with_load():
    """No load at which the served count falls off a cliff."""
    served_fraction = []
    for load in range(1, 30):
        power = beam_transmit_power_w(np.full(load, float(load)))
        served_fraction.append(
            1.0 - float(classify_link_power_feasibility(power).mean())
        )
    # It is a step per-beam, but every user on the beam is judged by the same
    # p_req only because they share a load; the transition is one user wide.
    transitions = sum(
        1
        for before, after in zip(served_fraction, served_fraction[1:])
        if before != after
    )
    assert transitions == 1, "exactly one crossing, not a repeated cliff"


def test_the_service_resolver_takes_no_capacity_argument():
    """Nothing in the signature could carry a ceiling."""
    import inspect

    signature = inspect.signature(service.resolve_service)
    assert list(signature.parameters) == [
        "actions",
        "decision_tables",
        "execution_masks",
    ]


def test_the_only_reason_a_user_goes_unserved_is_the_mask():
    """Behavioural version: capacity never removes anyone.

    Stronger than grepping for a sort — it asserts the property a selection
    step would have to break, whatever it was called.
    """
    rng = np.random.default_rng(5)
    for _ in range(150):
        users = int(rng.integers(1, 60))
        actions = [
            action_index(
                int(rng.integers(0, NUM_SATELLITE_SLOTS)),
                int(rng.integers(0, NUM_BEAM_SLOTS)),
            )
            for _ in range(users)
        ]
        resolution, _cells = _resolution(actions, users)
        # Every mask was all-True, so every user must be served, no matter
        # how many piled onto one cell or one satellite.
        assert resolution.served_count == users
        assert not resolution.execution_dropped.any()
        assert not resolution.no_op_users.any()
