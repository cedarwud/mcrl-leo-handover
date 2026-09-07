"""W-17 — the whole chain wired up, run against the real ephemeris.

Ruling F-1 resolved the ``p⁰``/``p_max`` collision by deriving
``p⁰ = p_max/2 = 0.825 W``, so the frozen constants are now consistent and
every test here runs on them.  ``FEASIBLE_PAIR`` is gone with the
contradiction it existed to work around.

What survives from that episode is the **compatibility condition**: the
ratio ``p_max/p⁰`` is a segment's gain budget, so anything that moves either
constant silently re-prices what "infeasible" means.  It is asserted here
rather than assumed.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    HandoverClass,
    decode_action,
)
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.geometry import angle_between_deg
from mcrl.env.interference import CANDIDATE_SINR_PROVENANCE
from mcrl.env.link_budget import (
    BEAM_POWER_MAX_W,
    SEGMENT_GAIN_BUDGET_DB,
    SEGMENT_START_EXCEEDS_BEAM_CEILING,
    SEGMENT_START_POWER_W,
    recurrence_power_w,
    segment_start_feasibility_report,
)
from mcrl.env.mobility import MobilityConfig
from mcrl.env.reference_policy import (
    RANDOM_MASKED,
    STAY_IF_POSSIBLE,
    build_reference_policy,
)
from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
from mcrl.env.service import load_balance_identity
from mcrl.env.step import PhysicsConfig, StepEnvironment
from mcrl.env.tle import TleArchive
from mcrl.errors import MCRLContractError
from mcrl.runtime.state_encoding import state_dim_for

_ARCHIVE = Path(TLE_ROOT_DEFAULT).expanduser()
requires_archive = pytest.mark.skipif(
    not _ARCHIVE.is_dir(), reason="TLE archive not present"
)
START = dt.datetime(2026, 8, 20, 6, 0, tzinfo=dt.timezone.utc)
USERS = 20

FROZEN = PhysicsConfig()
"""The frozen constants, which are now self-consistent (ruling F-1)."""


def _environment(physics=None, users=USERS):
    driver = ScenarioDriver(
        TleArchive(_ARCHIVE),
        ScenarioConfig(mobility=MobilityConfig(num_users=users)),
    )
    return StepEnvironment(driver, physics=physics)


def _run(env, policy_name=STAY_IF_POSSIBLE, seed=0, steps=None):
    policy = build_reference_policy(policy_name, seed=7)
    rng = np.random.default_rng(seed)
    observation = env.reset(START, rng)
    policy.reset()
    outcomes = []
    limit = steps or env.driver.config.steps_per_episode
    for _ in range(limit):
        actions = policy.act(observation.candidates, rng)
        outcome = env.step(actions, rng)
        outcomes.append(outcome)
        observation = outcome.observation
        if outcome.done:
            break
    return outcomes


# =========================================================================
# The frozen constants contradict each other
# =========================================================================


def test_p0_is_half_of_p_max_and_the_budget_is_3_dB():
    """Ruling F-1: ``p⁰ = p_max/2``, derived, not chosen."""
    assert BEAM_POWER_MAX_W == 1.65
    assert SEGMENT_START_POWER_W == pytest.approx(0.825)
    assert SEGMENT_START_POWER_W == BEAM_POWER_MAX_W / 2.0
    assert SEGMENT_GAIN_BUDGET_DB == pytest.approx(3.0103, abs=1e-4)
    assert SEGMENT_START_EXCEEDS_BEAM_CEILING is False

    report = segment_start_feasibility_report()
    assert report["every_segment_start_is_infeasible"] is False
    assert report["headroom_db"] == pytest.approx(3.0103, abs=1e-4)
    assert report["p0_is_below_saturation"] is True


def test_3_dB_is_the_cell_edge_which_is_why_the_budget_is_that_size():
    """``F(μ) = 0.5`` at ``μ = 2.07123`` ⇔ ``θ = θ_3dB/2`` ⇔ ``R_b``.

    The four quantities ``p⁰``, ``p_max``, ``θ_3dB`` and ``R_b`` are
    mutually consistent rather than independently chosen, and this is the
    identity that ties them.
    """
    from mcrl.env.antenna import THETA_3DB_DEG, mu_of, transmit_gain_linear

    half_angle = THETA_3DB_DEG / 2.0
    assert float(mu_of(np.array([half_angle]))[0]) == pytest.approx(
        2.07123, rel=1e-9
    )
    peak = float(transmit_gain_linear(np.array([0.0]))[0])
    edge = float(transmit_gain_linear(np.array([half_angle]))[0])
    assert edge / peak == pytest.approx(0.5, rel=1e-3)
    # ...and half the gain is exactly the budget p_max/p0 allows.
    assert BEAM_POWER_MAX_W / SEGMENT_START_POWER_W == pytest.approx(
        peak / edge, rel=1e-3
    )


def test_the_compatibility_condition_is_still_enforced():
    """It held for one day and cost a 100% outage rate; it stays checked."""
    contradictory = PhysicsConfig(segment_start_power_w=2.0)
    assert contradictory.segment_start_is_feasible is False
    assert PhysicsConfig().segment_start_is_feasible is True

    stand_in = StepEnvironment.__new__(StepEnvironment)
    stand_in.physics = contradictory
    with pytest.raises(MCRLContractError, match="exceeds p_max"):
        StepEnvironment.assert_ready_to_train(stand_in)


def test_training_is_refused_with_fading_switched_off():
    """The switch is a test affordance; a reported run keeps the draw."""
    stand_in = StepEnvironment.__new__(StepEnvironment)
    stand_in.physics = PhysicsConfig(fading_enabled=False)
    with pytest.raises(MCRLContractError, match="frozen seed set"):
        StepEnvironment.assert_ready_to_train(stand_in)


@requires_archive
def test_the_frozen_constants_now_serve_people():
    """The check ruling F-1 asked for: the outage rate is no longer 1.0."""
    environment = _environment(FROZEN)
    environment.assert_ready_to_train()
    outcomes = _run(environment)
    assert outcomes
    for outcome in outcomes:
        assert outcome.resolution.served_count > 0
        assert outcome.radiating.count > 0
        assert outcome.system_power_w > 0.0
        assert outcome.energy.zero_over_zero is False


@requires_archive
def test_a_segment_that_starts_above_the_ceiling_could_never_recover():
    """Why the collision was fatal rather than merely wasteful.

    (3.11) only ever *raises* power inside a segment — the gain falls, so
    the ratio exceeds one — which is what made a start above ``p_max`` an
    inescapable outage rather than a transient one.
    """
    environment = _environment(PhysicsConfig(segment_start_power_w=2.0))
    outcomes = _run(environment)
    for outcome in outcomes:
        assert outcome.resolution.served_count == 0
        assert int(np.count_nonzero(outcome.resolution.outage_infeasible)) == USERS
        assert outcome.radiating.count == 0
        assert outcome.energy.zero_over_zero is True


# =========================================================================
# The chain itself, under a stated consistent pair
# =========================================================================


@requires_archive
def test_the_state_is_112_wide():
    outcomes = _run(_environment(FROZEN), steps=1)
    observation = outcomes[0].observation
    assert observation.state_matrix.shape == (USERS, state_dim_for(NUM_ACTIONS))
    assert observation.state_matrix.shape[1] == 112
    assert observation.masks.shape == (USERS, NUM_ACTIONS)
    assert np.all(np.isfinite(observation.state_matrix))


@requires_archive
def test_every_served_link_has_a_finite_positive_sinr_and_rate():
    for outcome in _run(_environment(FROZEN)):
        served = outcome.resolution.served
        assert served.any(), "the consistent pair should serve somebody"
        assert np.all(outcome.link_sinr[served] > 0.0)
        assert np.all(np.isfinite(outcome.link_sinr))
        assert np.all(outcome.link_rate_bps[served] > 0.0)
        # Unserved users get zero, not a stale value from an earlier step.
        assert np.all(outcome.link_sinr[~served] == 0.0)
        assert np.all(outcome.link_rate_bps[~served] == 0.0)


@requires_archive
def test_the_sinr_lands_in_a_physically_sensible_band():
    """A link budget that is wrong by a factor is wrong by tens of dB.

    The band is deliberately wide — this is a units-and-sign check, not a
    calibration — but it catches the failures that matter: a missing ``/U``,
    degrees fed to a radian pattern (+44 dB), or FSPL applied as a gain.
    """
    outcome = _run(_environment(FROZEN), steps=1)[0]
    served = outcome.resolution.served
    sinr_db = 10.0 * np.log10(outcome.link_sinr[served])
    assert -10.0 < float(sinr_db.min()) < 40.0
    assert -10.0 < float(sinr_db.max()) < 40.0


@requires_archive
def test_interference_is_present_and_split_into_its_two_terms():
    outcome = _run(_environment(FROZEN), steps=1)[0]
    served = outcome.resolution.served
    total = outcome.interference.total_w[served]
    assert np.all(total > 0.0), "co-channel beams are radiating; I cannot be 0"
    assert np.allclose(
        outcome.interference.total_w,
        outcome.interference.intra_w + outcome.interference.inter_w,
    )
    fraction = outcome.interference.intra_fraction[served]
    assert np.all((fraction >= 0.0) & (fraction <= 1.0))


@requires_archive
def test_the_power_sum_is_per_beam_not_per_link():
    """Ruling F-2's regression, asked for by name: the ratio must be 1.0.

    ``link_over_beam_power_ratio`` is the reported ``P^N`` over an
    independently recomputed per-beam ``P^N``.  It read 2.28 while (3.16)
    was summed over links.  The superseded figure is still reported beside
    it, because the size of the correction is a finding — and because the
    defect was invisible in every other number a step produces.
    """
    for outcome in _run(_environment(FROZEN)):
        assert outcome.diagnostics["link_over_beam_power_ratio"] == 1.0
        superseded = float(
            outcome.diagnostics["superseded_link_over_beam_ratio"]
        )
        # It over-charges by (U - 1) * P^p per beam, so the ratio is a mean
        # occupancy weighted by P^p -- which can sit slightly ABOVE the plain
        # mean when the busier beams also draw more supply power.  The
        # bracketing statement is therefore max occupancy, not the mean.
        assert superseded >= 1.0
        busiest = max(outcome.resolution.eligible_load_by_beam.values())
        assert superseded <= busiest + 1e-9


@requires_archive
def test_the_load_identity_holds_through_the_environment():
    """G-4: ``Σ_u U_{b_u} = Σ_b U_b²``, on the beam-keyed loads."""
    for outcome in _run(_environment(FROZEN)):
        per_user, per_beam = load_balance_identity(outcome.resolution)
        assert per_user == pytest.approx(per_beam)


@requires_archive
def test_activation_equals_the_radiating_set():
    """``z = 1{U > 0}`` — derived, and the interference sum uses exactly it."""
    for outcome in _run(_environment(FROZEN)):
        assert outcome.radiating.count == len(outcome.resolution.active_beams)
        radiating = {
            (int(norad), int(cell))
            for norad, cell in zip(
                outcome.radiating.norad_ids.tolist(),
                outcome.radiating.cell_ids.tolist(),
            )
        }
        assert radiating == set(outcome.resolution.active_beams)


@requires_archive
def test_one_beam_radiates_one_power_no_matter_how_many_users():
    """``p_{s,v} = max_{u served} p_{u,s,v}`` — never a sum, never a mean."""
    for outcome in _run(_environment(FROZEN)):
        for index, (norad, cell) in enumerate(
            zip(
                outcome.radiating.norad_ids.tolist(),
                outcome.radiating.cell_ids.tolist(),
            )
        ):
            on_this_beam = [
                outcome.link_power_w[uid]
                for uid in range(USERS)
                if outcome.resolution.served[uid]
                and int(outcome.resolution.serving_satellite[uid]) == norad
                and int(outcome.resolution.serving_cell[uid]) == cell
            ]
            assert on_this_beam
            assert outcome.radiating.power_w[index] == pytest.approx(
                max(on_this_beam)
            )


# -- the recurrence (3.11)/(3.12) -----------------------------------------


@requires_archive
def test_the_product_p_times_gain_is_the_segment_invariant():
    """C-2: "段內不變量是 ``p·G^T`` 乘積,不是 ``p`` 本身".

    Held link, unchanged association: the transmit-side angle gain falls as
    the satellite moves off boresight and the power rises to compensate, so
    the product is constant at ``p⁰·G^T(θ(τ))`` for the whole segment.
    """
    from mcrl.env.antenna import transmit_gain_linear
    from mcrl.env.action_contract import decode_action

    env = _environment(FROZEN)
    policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
    rng = np.random.default_rng(3)
    observation = env.reset(START, rng)
    policy.reset()

    products: dict[int, list[float]] = {}
    associations: dict[int, list[tuple[int, int]]] = {}
    for _ in range(env.driver.config.steps_per_episode):
        actions = policy.act(observation.candidates, rng)
        candidates = observation.candidates
        outcome = env.step(actions, rng)
        for uid in range(USERS):
            if not outcome.resolution.served[uid]:
                products.pop(uid, None)
                associations.pop(uid, None)
                continue
            slot, beam = decode_action(int(actions[uid]))
            gain = float(
                transmit_gain_linear(
                    np.array([candidates.off_axis_deg[uid, slot, beam]])
                )[0]
            )
            key = (
                int(outcome.resolution.serving_satellite[uid]),
                int(outcome.resolution.serving_cell[uid]),
            )
            if associations.get(uid) and associations[uid][-1] != key:
                products[uid] = []
            associations.setdefault(uid, []).append(key)
            products.setdefault(uid, []).append(
                float(outcome.link_power_w[uid]) * gain
            )
        observation = outcome.observation
        if outcome.done:
            break

    held = [values for values in products.values() if len(values) >= 3]
    assert held, "no user held one association for three consecutive steps"
    for values in held:
        assert values[0] == pytest.approx(values[-1], rel=1e-9), (
            "p*G^T drifted inside a segment"
        )


@requires_archive
def test_a_cold_segment_starts_at_p0_exactly():
    """(3.12): ``p(τ) = p⁰``, with nothing yet to compensate."""
    cold = PhysicsConfig(segment_warm_start="none")
    outcome = _run(_environment(cold), steps=1)[0]
    served = outcome.resolution.served
    assert np.allclose(outcome.link_power_w[served], cold.segment_start_power_w)


@requires_archive
def test_the_warm_start_spreads_p0_instead_of_pinning_it():
    """The artefact it removes: ``p(0) = p⁰`` for 100% of users, every episode.

    A cold segment at every episode boundary is the same defect W-04 fixed
    for the D2 latches — the boundary is not a physical event.  With the
    warm start, ``p(0)`` is distributed across the 3 dB budget instead, and
    ``a = 0`` keeps positive probability so a genuinely fresh segment still
    happens; it just stops being certain.
    """
    outcome = _run(_environment(FROZEN), steps=1)[0]
    served = outcome.resolution.served
    powers = outcome.link_power_w[served]
    p0 = FROZEN.segment_start_power_w

    assert not np.allclose(powers, p0), "the warm start did nothing"
    assert powers.min() >= p0 - 1e-9, "p can never start BELOW p0"
    assert np.any(np.isclose(powers, p0)), "age 0 must still occur"
    assert np.any(powers > p0 + 0.01), "some segments must already be old"
    # Never past the ceiling: those users would be in outage instead.
    assert powers.max() <= FROZEN.beam_power_max_w


@requires_archive
def test_the_warm_start_is_reproducible_and_uses_the_environment_stream():
    first = _run(_environment(FROZEN), seed=3, steps=1)[0]
    again = _run(_environment(FROZEN), seed=3, steps=1)[0]
    assert np.array_equal(first.link_power_w, again.link_power_w)
    other = _run(_environment(FROZEN), seed=4, steps=1)[0]
    assert not np.array_equal(first.link_power_w, other.link_power_w)


@requires_archive
def test_each_user_warm_starts_from_its_own_segment_age(monkeypatch):
    """The episode boundary must not collapse distinct ages by NORAD id."""
    from mcrl.env.antenna import transmit_gain_linear

    forced_ages = np.resize(np.array([1, 2, 4, 7, 9]), USERS)
    monkeypatch.setattr(
        StepEnvironment,
        "_draw_segment_ages",
        lambda self, rng: forced_ages.copy(),
    )
    environment = _environment(FROZEN)
    rng = np.random.default_rng(13)
    observation = environment.reset(START, rng)
    actions = np.array(
        [int(np.flatnonzero(mask)[0]) for mask in observation.masks],
        dtype=np.int64,
    )

    user_ecef = environment.driver.user_ecef_km()
    expected = np.zeros(USERS, dtype=np.float64)
    wrong_max_age = np.zeros(USERS, dtype=np.float64)
    max_age_positions = environment.driver.satellite_ecef_at(
        -int(forced_ages.max())
    )
    for uid, action in enumerate(actions.tolist()):
        slot, beam = decode_action(action)
        association = observation.candidates.slot_tables[uid].association(action)
        current_gain = float(
            transmit_gain_linear(
                np.asarray(
                    [observation.candidates.off_axis_deg[uid, slot, beam]]
                )
            )[0]
        )

        def power_from(position: np.ndarray) -> float:
            start_angle = angle_between_deg(
                position,
                environment.driver.grid.centers_ecef_km[association.cell_id],
                user_ecef[uid],
            )
            start_gain = float(
                transmit_gain_linear(np.asarray([start_angle]))[0]
            )
            return float(
                recurrence_power_w(
                    start_gain,
                    current_gain,
                    p0_w=FROZEN.segment_start_power_w,
                )
            )

        own_age_positions = environment.driver.satellite_ecef_at(
            -int(forced_ages[uid])
        )
        expected[uid] = power_from(own_age_positions[association.norad_id])
        wrong_max_age[uid] = power_from(
            max_age_positions[association.norad_id]
        )

    assert not np.allclose(expected, wrong_max_age), (
        "the fixture must distinguish per-user ages from the overwritten age"
    )
    outcome = environment.step(actions, rng)
    assert np.allclose(outcome.link_power_w, expected, rtol=1e-12, atol=1e-12)


def test_the_sensitivity_arm_needs_its_frozen_L():
    """``uniform-segment-length`` is the frozen second arm, not a free option."""
    PhysicsConfig(segment_warm_start="uniform-segment-length", segment_age_steps=6)
    with pytest.raises(ValueError, match="frozen segment_age_steps"):
        PhysicsConfig(segment_warm_start="uniform-segment-length")


@requires_archive
def test_the_recurrence_never_survives_a_handover():
    """One of C-2's five break events, checked on the realised association."""
    env = _environment(FROZEN)
    # RANDOM_MASKED, not NEAREST_ELIGIBLE: the point is to *cause* handovers.
    # A stay-ish policy can go a whole episode without one and the test would
    # then skip, which proves nothing about the break rule.
    policy = build_reference_policy(RANDOM_MASKED, seed=7)
    rng = np.random.default_rng(5)
    observation = env.reset(START, rng)
    policy.reset()

    previous: dict[int, tuple[int, int]] = {}
    checked = 0
    for _ in range(env.driver.config.steps_per_episode):
        actions = policy.act(observation.candidates, rng)
        outcome = env.step(actions, rng)
        for uid in range(USERS):
            if not outcome.resolution.served[uid]:
                previous.pop(uid, None)
                continue
            key = (
                int(outcome.resolution.serving_satellite[uid]),
                int(outcome.resolution.serving_cell[uid]),
            )
            if uid in previous and previous[uid] != key:
                assert outcome.link_power_w[uid] == pytest.approx(
                    FROZEN.segment_start_power_w
                ), "a handover must restart the segment at p0"
                checked += 1
            previous[uid] = key
        observation = outcome.observation
        if outcome.done:
            break
    assert checked > 0, "the random policy produced no handover to check"


# -- the state blocks -----------------------------------------------------


@requires_archive
def test_the_first_state_has_no_previous_connection_no_demand_and_no_interference():
    env = _environment(FROZEN)
    observation = env.reset(START, np.random.default_rng(0))
    access = observation.state_matrix[:, :NUM_ACTIONS]
    loads = observation.state_matrix[:, 3 * NUM_ACTIONS :]
    assert not access.any(), "nothing was connected before step 0"
    assert not loads.any(), "no demand existed before step 0"
    # Nothing is radiating, so every candidate SINR is a pure SNR.
    assert np.all(observation.candidate_sinr >= 0.0)
    assert observation.sinr_provenance == CANDIDATE_SINR_PROVENANCE


@requires_archive
def test_the_previous_connection_block_marks_the_incumbent():
    env = _environment(FROZEN)
    outcomes = _run(env, steps=2)
    first, second = outcomes[0], outcomes[1]
    access = second.observation.state_matrix[:, :NUM_ACTIONS]
    for uid in range(USERS):
        if not second.resolution.served[uid]:
            continue
        marked = np.flatnonzero(access[uid])
        assert marked.size <= 1, "x(t-1) is a one-hot, not a set"
    del first


@requires_archive
def test_the_load_block_is_the_previous_steps_demand_keyed_by_beam():
    env = _environment(FROZEN)
    outcomes = _run(env, steps=2)
    table = outcomes[1].observation.candidates
    loads = outcomes[1].observation.state_matrix[:, 3 * NUM_ACTIONS :]
    demand = outcomes[0].resolution.demand_by_beam
    for uid in range(USERS):
        slot_table = table.slot_tables[uid]
        for action in range(NUM_ACTIONS):
            norad = int(slot_table.norad_ids[action])
            cell = int(slot_table.cell_ids[action])
            expected = demand.get((norad, cell), 0) if norad >= 0 and cell >= 0 else 0
            assert loads[uid, action] == pytest.approx(expected / USERS)


@requires_archive
def test_theta_reaches_the_state_in_radians():
    """G-7's units seam: degrees here would inflate every angle 57.3x."""
    observation = _environment(FROZEN).reset(START, np.random.default_rng(0))
    theta = observation.state_matrix[:, 2 * NUM_ACTIONS : 3 * NUM_ACTIONS]
    assert float(np.abs(theta).max()) <= np.pi
    assert float(np.abs(theta).max()) > 0.0


# -- reward wiring --------------------------------------------------------


@requires_archive
def test_r1_is_energy_efficiency_and_sums_to_the_system_figure():
    """(3.25): ``r1`` decomposes the system EE exactly, by construction."""
    for outcome in _run(_environment(FROZEN)):
        r1 = outcome.reward_matrix[:, 0]
        assert float(r1.sum()) == pytest.approx(
            outcome.energy.system_ee_bits_per_j, rel=1e-9
        )


@requires_archive
def test_r2_is_zero_on_the_first_step_and_negative_on_a_handover():
    outcomes = _run(_environment(FROZEN))
    assert all(
        handover is HandoverClass.NONE for handover in outcomes[0].handovers
    ), "the first step of an episode is never a handover"
    assert np.all(outcomes[0].reward_matrix[:, 1] == 0.0)
    for outcome in outcomes:
        assert np.all(outcome.reward_matrix[:, 1] <= 0.0)


@requires_archive
def test_r3_is_the_negative_beam_load():
    for outcome in _run(_environment(FROZEN)):
        r3 = outcome.reward_matrix[:, 2]
        assert np.all(r3 <= 0.0)
        assert np.array_equal(-r3, outcome.resolution.user_beam_load())


# -- reproducibility ------------------------------------------------------


@requires_archive
def test_the_same_seed_gives_the_same_episode():
    """Including the fading draw, which is keyed by sorted NORAD id."""
    first = _run(_environment(FROZEN), seed=11)
    second = _run(_environment(FROZEN), seed=11)
    assert len(first) == len(second)
    for left, right in zip(first, second):
        assert np.array_equal(left.reward_matrix, right.reward_matrix)
        assert np.allclose(left.link_sinr, right.link_sinr)
        assert left.system_power_w == right.system_power_w


@requires_archive
def test_a_different_seed_moves_the_fading_but_not_the_geometry():
    first = _run(_environment(FROZEN), seed=11)[0]
    second = _run(_environment(FROZEN), seed=12)[0]
    assert not np.allclose(first.link_sinr, second.link_sinr)


@requires_archive
def test_candidate_sinr_reuses_the_overlap_path_fading(monkeypatch):
    """One user/satellite path gets one fading draw in an observation."""
    from mcrl.env import step as step_module

    environment = _environment(FROZEN)
    rng = np.random.default_rng(0)
    observation = environment.reset(START, rng)
    actions = np.array(
        [int(np.flatnonzero(mask)[0]) for mask in observation.masks],
        dtype=np.int64,
    )

    def window_norads(candidates):
        return {
            int(norad)
            for norad in candidates.window_norad_ids.reshape(-1)
            if int(norad) >= 0
        }

    decision_ids = window_norads(observation.candidates)
    rician_elements = []
    shadow_elements = []
    original_rician = step_module.rician_fading_gain
    original_shadow = step_module.shadow_fading_db

    def record_rician(*args, **kwargs):
        value = original_rician(*args, **kwargs)
        rician_elements.append(np.asarray(value).size)
        return value

    def record_shadow(*args, **kwargs):
        value = original_shadow(*args, **kwargs)
        shadow_elements.append(np.asarray(value).size)
        return value

    monkeypatch.setattr(step_module, "rician_fading_gain", record_rician)
    monkeypatch.setattr(step_module, "shadow_fading_db", record_shadow)

    outcome = environment.step(actions, rng)
    next_ids = window_norads(outcome.observation.candidates)
    previous_ids = {
        int(norad) for norad in outcome.radiating.norad_ids.tolist()
    }
    overlap = next_ids & previous_ids
    assert overlap, "the fixture must exercise candidate/previous overlap"

    expected_vectors = (
        len(decision_ids) + len(next_ids) + len(previous_ids - next_ids)
    )
    expected_elements = environment.num_users * expected_vectors
    assert sum(rician_elements) == expected_elements
    assert sum(shadow_elements) == expected_elements


# -- fail-closed ----------------------------------------------------------


@requires_archive
def test_an_action_the_mask_forbids_is_refused():
    """P-4 runs inside ``env.step``, not only in the caller.

    Note the mask is currently 28/28 in this configuration — the three
    geometric terms are all non-binding at these elevations — so a
    masked-off action does not exist to try.  An out-of-range index goes
    through the same validator and is the case that can always be built,
    with the masked-off one added whenever the geometry supplies it.
    """
    env = _environment(FROZEN)
    observation = env.reset(START, np.random.default_rng(0))

    actions = np.zeros(USERS, dtype=np.int64)
    actions[0] = NUM_ACTIONS
    with pytest.raises(MCRLContractError, match="out of range"):
        env.step(actions, np.random.default_rng(0))

    forbidden = np.flatnonzero(~observation.masks[0])
    if forbidden.size:
        actions[0] = int(forbidden[0])
        with pytest.raises(MCRLContractError, match="invalid under its own mask"):
            env.step(actions, np.random.default_rng(0))


@requires_archive
def test_a_no_op_with_valid_actions_available_is_refused():
    env = _environment(FROZEN)
    observation = env.reset(START, np.random.default_rng(0))
    if observation.masks[0].sum() == 0:
        pytest.skip("user 0 is starved, so a no-op is legal")
    actions = np.zeros(USERS, dtype=np.int64)
    actions[0] = NO_OP_ACTION
    with pytest.raises(MCRLContractError, match="no-op"):
        env.step(actions, np.random.default_rng(0))


def test_stepping_before_reset_is_refused():
    env = StepEnvironment.__new__(StepEnvironment)
    env._started = False
    env._candidates = None
    with pytest.raises(MCRLContractError, match="not been reset"):
        StepEnvironment.step(env, np.zeros(1, dtype=np.int64), np.random.default_rng(0))


@requires_archive
def test_the_warm_start_ages_do_not_share_a_stream_with_the_fading():
    """A fading ablation must not silently re-draw the entry ages.

    They shared ``env_rng`` until 2026-08-23, so turning fading off shifted
    every later episode's ages and the outage count moved (95 versus 106)
    from ages that were supposed to be identical.  The ages now come from a
    generator spawned once, so the two are independent — the same argument
    that separated ``env_rng`` from ``mobility_rng``.
    """
    def ages(fading: bool) -> np.ndarray:
        environment = _environment(PhysicsConfig(fading_enabled=fading))
        drawn = []
        env_rng = np.random.default_rng(5)
        mobility_rng = np.random.default_rng(6)
        for _ in range(3):
            environment.reset(START, env_rng, mobility_rng=mobility_rng)
            drawn.append(environment._pending_segment_age.copy())
        return np.concatenate(drawn)

    assert np.array_equal(ages(True), ages(False))


@requires_archive
def test_the_feasibility_verdict_does_not_read_the_fading():
    """``p = p⁰·G(τ)/G(t)`` is transmit pattern only; ``L_s`` lives in ``H``.

    So the outage set is a function of the geometry and the entry ages, and
    the fading draw moves the SINR without moving who is served.  It is
    what lets a reported outage rate be reproducible from a stated seed
    rather than being an average over fading realisations.
    """
    def run(fading: bool):
        environment = _environment(PhysicsConfig(fading_enabled=fading))
        policy = build_reference_policy(STAY_IF_POSSIBLE, seed=7)
        env_rng = np.random.default_rng(5)
        mobility_rng = np.random.default_rng(6)
        action_rng = np.random.default_rng(7)
        observation = environment.reset(START, env_rng, mobility_rng=mobility_rng)
        policy.reset()
        outage, sinr = [], []
        while True:
            outcome = environment.step(
                policy.act(observation.candidates, action_rng), env_rng
            )
            outage.append(outcome.resolution.outage_infeasible.copy())
            sinr.append(outcome.link_sinr.copy())
            observation = outcome.observation
            if outcome.done:
                break
        return np.stack(outage), np.stack(sinr)

    outage_on, sinr_on = run(True)
    outage_off, sinr_off = run(False)
    assert np.array_equal(outage_on, outage_off), (
        "the fading draw changed who was served"
    )
    assert not np.allclose(sinr_on, sinr_off), (
        "fading must still move the SINR, or this test proves nothing"
    )
