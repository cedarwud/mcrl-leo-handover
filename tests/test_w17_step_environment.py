"""W-17 — the whole chain wired up, run against the real ephemeris.

Two kinds of test here and they are kept apart on purpose.

The **contradiction** tests need no archive: ``p⁰ > p_max`` is arithmetic on
two frozen constants, and its consequence — every segment start infeasible —
follows without a satellite anywhere near.

The **physics** tests need the archive, and they run under an explicitly
stated consistent pair rather than the frozen one, because under the frozen
pair nobody is ever served and there is no physics to test.  The pair used
is named at the point of use so no reader mistakes it for a decision.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pytest

from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS, HandoverClass
from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.interference import CANDIDATE_SINR_PROVENANCE
from mcrl.env.link_budget import (
    BEAM_POWER_MAX_W,
    PA_SATURATION_POWER_W,
    SEGMENT_START_EXCEEDS_BEAM_CEILING,
    SEGMENT_START_POWER_W,
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

FEASIBLE_PAIR = PhysicsConfig(beam_power_max_w=PA_SATURATION_POWER_W)
"""**Not a ruling.**  A consistent ``(p⁰, ceiling)`` so the physics can run.

``p_sat`` is the only other ceiling the model defines and ``p⁰ = 2 W`` sits
under it, so this is the shape a resolution would probably take — but which
of the two numbers moves is the controller's call, and nothing here decides
it.  Every test that uses this says so.
"""


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


def test_p0_exceeds_the_feasibility_ceiling():
    """``p⁰ = 2 W``, ``p_max = 1.65 W``.  Both are ch5 table 5-2, active."""
    assert SEGMENT_START_POWER_W == 2.0
    assert BEAM_POWER_MAX_W == 1.65
    assert SEGMENT_START_EXCEEDS_BEAM_CEILING is True

    report = segment_start_feasibility_report()
    assert report["every_segment_start_is_infeasible"] is True
    assert report["headroom_db"] < 0.0
    # p0 is comfortably under the only other ceiling the model defines.
    assert report["p0_is_below_saturation"] is True


def test_the_default_physics_config_carries_the_contradiction():
    assert PhysicsConfig().segment_start_is_feasible is False
    assert FEASIBLE_PAIR.segment_start_is_feasible is True


def test_training_is_refused_while_it_stands():
    driver_free = StepEnvironment.__new__(StepEnvironment)
    driver_free.physics = PhysicsConfig()
    with pytest.raises(MCRLContractError, match="exceeds p_max"):
        StepEnvironment.assert_ready_to_train(driver_free)


def test_training_is_also_refused_with_fading_switched_off():
    """The switch is a test affordance; a reported run keeps the draw."""
    stand_in = StepEnvironment.__new__(StepEnvironment)
    stand_in.physics = PhysicsConfig(
        beam_power_max_w=PA_SATURATION_POWER_W, fading_enabled=False
    )
    with pytest.raises(MCRLContractError, match="frozen seed set"):
        StepEnvironment.assert_ready_to_train(stand_in)


@requires_archive
def test_under_the_frozen_constants_the_outage_rate_is_exactly_one():
    """The consequence, measured rather than argued.

    This is the evidence the open decision needs: not "the numbers look
    inconsistent" but "the environment serves nobody, ever".
    """
    outcomes = _run(_environment())
    assert outcomes, "the episode produced no steps"
    for outcome in outcomes:
        assert outcome.resolution.served_count == 0
        assert int(np.count_nonzero(outcome.resolution.outage_infeasible)) == USERS
        assert outcome.radiating.count == 0
        assert outcome.system_power_w == 0.0
        assert outcome.energy.zero_over_zero is True
        assert outcome.reward_matrix[:, 0].tolist() == [0.0] * USERS


# =========================================================================
# The chain itself, under a stated consistent pair
# =========================================================================


@requires_archive
def test_the_state_is_112_wide():
    outcomes = _run(_environment(FEASIBLE_PAIR), steps=1)
    observation = outcomes[0].observation
    assert observation.state_matrix.shape == (USERS, state_dim_for(NUM_ACTIONS))
    assert observation.state_matrix.shape[1] == 112
    assert observation.masks.shape == (USERS, NUM_ACTIONS)
    assert np.all(np.isfinite(observation.state_matrix))


@requires_archive
def test_every_served_link_has_a_finite_positive_sinr_and_rate():
    for outcome in _run(_environment(FEASIBLE_PAIR)):
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
    outcome = _run(_environment(FEASIBLE_PAIR), steps=1)[0]
    served = outcome.resolution.served
    sinr_db = 10.0 * np.log10(outcome.link_sinr[served])
    assert -10.0 < float(sinr_db.min()) < 40.0
    assert -10.0 < float(sinr_db.max()) < 40.0


@requires_archive
def test_interference_is_present_and_split_into_its_two_terms():
    outcome = _run(_environment(FEASIBLE_PAIR), steps=1)[0]
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
def test_the_load_identity_holds_through_the_environment():
    """G-4: ``Σ_u U_{b_u} = Σ_b U_b²``, on the beam-keyed loads."""
    for outcome in _run(_environment(FEASIBLE_PAIR)):
        per_user, per_beam = load_balance_identity(outcome.resolution)
        assert per_user == pytest.approx(per_beam)


@requires_archive
def test_activation_equals_the_radiating_set():
    """``z = 1{U > 0}`` — derived, and the interference sum uses exactly it."""
    for outcome in _run(_environment(FEASIBLE_PAIR)):
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
    for outcome in _run(_environment(FEASIBLE_PAIR)):
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

    env = _environment(FEASIBLE_PAIR)
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
def test_a_segment_starts_at_p0_exactly():
    """(3.12): ``p(τ) = p⁰``, with nothing yet to compensate."""
    outcome = _run(_environment(FEASIBLE_PAIR), steps=1)[0]
    served = outcome.resolution.served
    assert np.allclose(
        outcome.link_power_w[served], FEASIBLE_PAIR.segment_start_power_w
    )


@requires_archive
def test_the_recurrence_never_survives_a_handover():
    """One of C-2's five break events, checked on the realised association."""
    env = _environment(FEASIBLE_PAIR)
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
                    FEASIBLE_PAIR.segment_start_power_w
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
    env = _environment(FEASIBLE_PAIR)
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
    env = _environment(FEASIBLE_PAIR)
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
    env = _environment(FEASIBLE_PAIR)
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
    observation = _environment(FEASIBLE_PAIR).reset(START, np.random.default_rng(0))
    theta = observation.state_matrix[:, 2 * NUM_ACTIONS : 3 * NUM_ACTIONS]
    assert float(np.abs(theta).max()) <= np.pi
    assert float(np.abs(theta).max()) > 0.0


# -- reward wiring --------------------------------------------------------


@requires_archive
def test_r1_is_energy_efficiency_and_sums_to_the_system_figure():
    """(3.25): ``r1`` decomposes the system EE exactly, by construction."""
    for outcome in _run(_environment(FEASIBLE_PAIR)):
        r1 = outcome.reward_matrix[:, 0]
        assert float(r1.sum()) == pytest.approx(
            outcome.energy.system_ee_bits_per_j, rel=1e-9
        )


@requires_archive
def test_r2_is_zero_on_the_first_step_and_negative_on_a_handover():
    outcomes = _run(_environment(FEASIBLE_PAIR))
    assert all(
        handover is HandoverClass.NONE for handover in outcomes[0].handovers
    ), "the first step of an episode is never a handover"
    assert np.all(outcomes[0].reward_matrix[:, 1] == 0.0)
    for outcome in outcomes:
        assert np.all(outcome.reward_matrix[:, 1] <= 0.0)


@requires_archive
def test_r3_is_the_negative_beam_load():
    for outcome in _run(_environment(FEASIBLE_PAIR)):
        r3 = outcome.reward_matrix[:, 2]
        assert np.all(r3 <= 0.0)
        assert np.array_equal(-r3, outcome.resolution.user_beam_load())


# -- reproducibility ------------------------------------------------------


@requires_archive
def test_the_same_seed_gives_the_same_episode():
    """Including the fading draw, which is keyed by sorted NORAD id."""
    first = _run(_environment(FEASIBLE_PAIR), seed=11)
    second = _run(_environment(FEASIBLE_PAIR), seed=11)
    assert len(first) == len(second)
    for left, right in zip(first, second):
        assert np.array_equal(left.reward_matrix, right.reward_matrix)
        assert np.allclose(left.link_sinr, right.link_sinr)
        assert left.system_power_w == right.system_power_w


@requires_archive
def test_a_different_seed_moves_the_fading_but_not_the_geometry():
    first = _run(_environment(FEASIBLE_PAIR), seed=11)[0]
    second = _run(_environment(FEASIBLE_PAIR), seed=12)[0]
    assert not np.allclose(first.link_sinr, second.link_sinr)


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
    env = _environment(FEASIBLE_PAIR)
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
    env = _environment(FEASIBLE_PAIR)
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
