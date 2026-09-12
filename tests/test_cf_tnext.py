"""CF2S-LANE-N — ``T_NEXT`` contract tests and the named mutant table.

Amendment 15 §2A froze the source; this file pins each clause of it with a
check, and asserts that a **named mutation** of the implementation makes a
**named check** red.  The pattern is the one the B1 lane used: every check runs
green against the real code, and every mutant is tied to the check it must
break, so "the tests pass" is a statement about discrimination rather than
about coverage.

The environment-backed checks need the pinned TLE archive and skip cleanly
when it is not reachable, so the pure-logic checks still run anywhere.  The
archive is parsed once per module; the environment itself is rebuilt per test
because several mutants deliberately corrupt it.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

import numpy as np
import pytest

from mcrl.algorithms import cf_teacher as cft
from mcrl.algorithms import cf_tnext as tn
from mcrl.env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from mcrl.errors import MCRLContractError

P0_ENV_SEED, P0_MOB_SEED = 9_202_500, 9_203_500


# --------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def archive():
    tp = pytest.importorskip("mcrl.runtime.training_pipeline")
    try:
        tp.assert_tle_archive_pinned()
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"pinned TLE archive unavailable: {exc}")
    from mcrl.env.tle import TleArchive

    return TleArchive(tp.resolve_tle_root())


@pytest.fixture
def live(archive):
    """A fresh environment at the frozen P0 seed pair, advanced to step 1.

    Step 1 rather than step 0: §3 wants history-carrying states, and a reset
    state has no incumbent, which would hide the association-persistence
    structure the source is about.  The fixture is per-test because mutants
    M1 and M1b corrupt the environment on purpose.
    """
    from mcrl.algorithms.cf_ratio import make_env_on

    env = make_env_on(archive, 100)
    env_rng = np.random.default_rng(P0_ENV_SEED)
    mob_rng = np.random.default_rng(P0_MOB_SEED)
    states, masks, _ = env.reset(env_rng, mob_rng)
    _, t0_acts, _ = cft.t0_scores(states, masks)
    result = env.step(t0_acts, env_rng)
    return {
        "env": env,
        "driver": env.environment.driver,
        "states": list(result.user_states),
        "masks": list(result.action_masks),
        "candidates": env.last_outcome.observation.candidates,
        "env_rng": env_rng,
    }


# ------------------------------------------------------------ synthetic bed
@dataclass
class Bed:
    """A hand-built one-user ranking problem with a known right answer."""

    legal: np.ndarray
    persists: np.ndarray
    gain: np.ndarray
    score: np.ndarray


def _bed() -> Bed:
    return Bed(
        np.zeros(NUM_ACTIONS, dtype=bool),
        np.zeros(NUM_ACTIONS, dtype=bool),
        np.zeros(NUM_ACTIONS, dtype=np.float64),
        np.zeros(NUM_ACTIONS, dtype=np.float64),
    )


def _snapshot(live) -> dict:
    """Everything about the environment a lookahead could disturb."""
    driver = live["driver"]
    users = driver._users
    return {
        "env_rng": copy.deepcopy(live["env_rng"].bit_generator.state),
        "step_index": driver.step_index,
        "start_utc": str(driver._start_utc),
        "user_xy": np.array(users.positions_km, copy=True),
        "user_heading": np.array(users.headings_rad, copy=True),
        "user_ecef": np.array(driver.user_ecef_km(), copy=True),
        "frozen_window": copy.deepcopy(driver._frozen_window_norad_ids),
        "tracked": np.array(driver.tracked_norad_ids, copy=True),
        "d2": copy.deepcopy(driver._tracker.__dict__),
        "dwell": copy.deepcopy(driver._dwell.__dict__),
        "env_state": copy.deepcopy(live["env"].environment.training_state_dict()),
    }


def _identical(a, b, path: str = "") -> None:
    if isinstance(a, np.ndarray) or isinstance(b, np.ndarray):
        assert np.array_equal(
            np.asarray(a), np.asarray(b), equal_nan=np.asarray(a).dtype.kind == "f"
        ), f"{path} changed"
        return
    if isinstance(a, dict):
        assert set(a) == set(b), f"{path} keys changed"
        for key in a:
            _identical(a[key], b[key], f"{path}.{key}")
        return
    if isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{path} length changed"
        for i, (x, y) in enumerate(zip(a, b)):
            _identical(x, y, f"{path}[{i}]")
        return
    if a is None or b is None:
        assert a is None and b is None, f"{path} changed: {a!r} -> {b!r}"
        return
    if hasattr(a, "__dict__") and not isinstance(a, (str, bytes, int, float, bool)):
        # Dataclasses holding arrays (CellGrid, D2Tracker, DwellController)
        # have an ``__eq__`` that returns an array, so recurse structurally.
        _identical(vars(a), vars(b), path)
        return
    assert a == b, f"{path} changed: {a!r} -> {b!r}"


# ------------------------------------------------------------------ checks
# Each check raises AssertionError (or MCRLContractError) when the property it
# names is violated.  ``rank`` / ``geom`` / ``act`` / ``identity`` are injected
# so a mutant can replace exactly one of them and nothing else.


def check_persistence_dominates_gain(rank: Callable, **_) -> None:
    """Term 1 outranks term 2: a persisting association wins even against a
    non-persisting one with far more nominal next-step gain."""
    bed = _bed()
    bed.legal[[3, 9]] = True
    bed.persists[3] = True
    bed.gain[3], bed.gain[9] = 1.0, 1e9
    assert rank(bed.legal, bed.persists, bed.gain, bed.score) == 3


def check_gain_dominates_t0_score(rank: Callable, **_) -> None:
    """Term 2 outranks term 3."""
    bed = _bed()
    bed.legal[[3, 9]] = True
    bed.persists[[3, 9]] = True
    bed.gain[3], bed.gain[9] = 1.0, 2.0
    bed.score[3], bed.score[9] = 100.0, -100.0
    assert rank(bed.legal, bed.persists, bed.gain, bed.score) == 9


def check_t0_score_dominates_index(rank: Callable, **_) -> None:
    """Term 3 outranks term 4."""
    bed = _bed()
    bed.legal[[3, 9]] = True
    bed.persists[[3, 9]] = True
    bed.gain[[3, 9]] = 5.0
    bed.score[3], bed.score[9] = -1.0, 1.0
    assert rank(bed.legal, bed.persists, bed.gain, bed.score) == 9


def check_ties_break_on_lowest_index(rank: Callable, **_) -> None:
    """Term 4: a full tie goes to the LOWEST index — ``-current_action_index``
    ranked 'higher is better', the project's first-index-on-ties convention."""
    bed = _bed()
    bed.legal[[2, 5, 20]] = True
    bed.persists[[2, 5, 20]] = True
    bed.gain[[2, 5, 20]] = 7.0
    bed.score[[2, 5, 20]] = 3.0
    assert rank(bed.legal, bed.persists, bed.gain, bed.score) == 2


def check_illegal_action_is_unreachable(rank: Callable, **_) -> None:
    """An illegal action can never be selected, however attractive."""
    bed = _bed()
    bed.legal[4] = True
    bed.persists[:] = True
    bed.gain[:] = 1.0
    bed.gain[17] = 1e12
    bed.score[17] = 1e12
    chosen = rank(bed.legal, bed.persists, bed.gain, bed.score)
    assert chosen == 4 and bool(bed.legal[chosen])


def check_empty_mask_is_no_op(rank: Callable, **_) -> None:
    bed = _bed()
    assert rank(bed.legal, bed.persists, bed.gain, bed.score) == NO_OP_ACTION


def check_source_identity_in_hash(identity: Callable, **_) -> None:
    """Amendment 15 §6: the config hash must carry the source identity."""
    import hashlib
    import json

    payload = identity()
    blob = json.dumps(payload, sort_keys=True, default=str)
    assert tn.SOURCE_ID in blob, "the hashed payload does not name the source"
    assert tn.SOURCE_VERSION in blob, "the hashed payload carries no version"
    other = dict(payload)
    other["source_id"] = "T_TAIL"
    assert hashlib.sha256(blob.encode()).hexdigest() != hashlib.sha256(
        json.dumps(other, sort_keys=True, default=str).encode()
    ).hexdigest(), "two different sources hash the same"


def check_lookahead_is_side_effect_free(geom: Callable, live=None, **_) -> None:
    """§2A clause 3, the required proof.

    Every generator the environment holds and every piece of scenario state it
    carries is captured before and after a lookahead and must come back
    bit-identical.  The env generator is included explicitly because the
    fading draw is the one stream a careless lookahead would consume, and the
    user positions and headings because they are the mobility stream's only
    observable.
    """
    before = _snapshot(live)
    geom(live["driver"], live["candidates"])
    after = _snapshot(live)
    _identical(before, after, "env")


def check_lookahead_is_deterministic(geom: Callable, live=None, **_) -> None:
    """No future stochastic fading: two lookaheads are bit-identical."""
    first = geom(live["driver"], live["candidates"])
    second = geom(live["driver"], live["candidates"])
    for field in ("persists", "nominal_gain", "elevation_deg", "off_axis_deg"):
        assert np.array_equal(
            getattr(first, field), getattr(second, field), equal_nan=True
        ), f"{field} is not deterministic across two lookaheads"


def check_lookahead_reads_the_next_step(geom: Callable, live=None, **_) -> None:
    """The lookahead must use ``t+1`` geometry, not ``t`` geometry.

    At ``Δt = 30.08 s`` a tracked satellite moves ≈ 220 km, so the two are far
    apart; an offset-zero lookahead would silently turn ``T_NEXT`` into a
    current-step gain rule while every other check still passed.
    """
    candidates = live["candidates"]
    result = geom(live["driver"], candidates)
    legal = candidates.masks
    now = np.repeat(candidates.elevation_deg, 7, axis=1)
    delta = np.abs(result.elevation_deg[legal] - now[legal])
    assert float(np.nanmean(delta)) > 1.0, (
        "t+1 elevations are indistinguishable from t elevations; the lookahead "
        "is not advancing the ephemeris"
    )


def check_association_not_slot_identity(geom: Callable, live=None, **_) -> None:
    """The ``t+1`` geometry must be keyed on the association resolved at ``t``.

    Constructive: for every legal action, the satellite whose ``t+1`` position
    produced the slant range must be the NORAD id the ``t`` slot table names.
    A raw-slot-persistence implementation reads whatever occupies that slot
    number instead, and fails here.  §2A forbids exactly that approximation.
    """
    driver, candidates = live["driver"], live["candidates"]
    result = geom(driver, candidates)
    positions = driver.satellite_ecef_at(1)
    user_ecef = driver.user_ecef_km()
    checked = 0
    for uid in range(0, len(candidates.slot_tables), 7):
        table = candidates.slot_tables[uid]
        for action in np.flatnonzero(table.mask).tolist():
            norad = int(table.norad_ids[action])
            expected = float(np.linalg.norm(positions[norad] - user_ecef[uid]))
            assert abs(result.slant_range_km[uid, action] - expected) < 1e-6, (
                f"user {uid} action {action}: the t+1 slant range is not that of "
                f"NORAD {norad}, the association resolved at t"
            )
            checked += 1
    assert checked > 0


def check_final_step_is_t0(act: Callable, live=None, **_) -> None:
    """§2A: the final decision step falls back deterministically to T0."""
    states, masks = live["states"], live["masks"]
    _, t0_acts, _ = cft.t0_scores(states, masks)
    kwargs = dict(
        driver=live["driver"], candidates=live["candidates"], is_final_step=True
    )
    actions, diag, geometry = act(states, masks, **kwargs)
    assert geometry is None, "the final step must not run a lookahead at all"
    assert np.array_equal(np.asarray(actions), np.asarray(t0_acts)), (
        "the final-step fallback is not T0"
    )
    again, _, _ = act(states, masks, **kwargs)
    assert np.array_equal(np.asarray(actions), np.asarray(again)), (
        "the final-step fallback is not deterministic"
    )
    assert diag["fallback_final_step"] == diag["decisions"] > 0


def check_actions_are_legal_and_repeatable(act: Callable, live=None, **_) -> None:
    states, masks = live["states"], live["masks"]
    kwargs = dict(
        driver=live["driver"], candidates=live["candidates"], is_final_step=False
    )
    first, _, _ = act(states, masks, **kwargs)
    second, _, _ = act(states, masks, **kwargs)
    assert np.array_equal(np.asarray(first), np.asarray(second)), (
        "T_NEXT is not deterministically repeatable"
    )
    for uid, action in enumerate(np.asarray(first).tolist()):
        if action == NO_OP_ACTION:
            assert not bool(masks[uid].mask.any())
        else:
            assert bool(masks[uid].mask[action]), (
                f"user {uid} was given illegal action {action}"
            )


CHECKS: dict[str, tuple[Callable, bool]] = {
    "persistence_dominates_gain": (check_persistence_dominates_gain, False),
    "gain_dominates_t0_score": (check_gain_dominates_t0_score, False),
    "t0_score_dominates_index": (check_t0_score_dominates_index, False),
    "ties_break_on_lowest_index": (check_ties_break_on_lowest_index, False),
    "illegal_action_is_unreachable": (check_illegal_action_is_unreachable, False),
    "empty_mask_is_no_op": (check_empty_mask_is_no_op, False),
    "source_identity_in_hash": (check_source_identity_in_hash, False),
    "lookahead_is_side_effect_free": (check_lookahead_is_side_effect_free, True),
    "lookahead_is_deterministic": (check_lookahead_is_deterministic, True),
    "lookahead_reads_the_next_step": (check_lookahead_reads_the_next_step, True),
    "association_not_slot_identity": (check_association_not_slot_identity, True),
    "final_step_is_t0": (check_final_step_is_t0, True),
    "actions_are_legal_and_repeatable": (check_actions_are_legal_and_repeatable, True),
}


def _real() -> dict:
    return {
        "rank": tn.rank_legal_actions,
        "geom": tn.next_step_geometry,
        "act": tn.tnext_actions,
        "identity": tn.source_identity,
    }


def _pick(keys, persists, gain, score, indices) -> int:
    return int(indices[keys.index(max(keys))])


# ----------------------------------------------------------------- mutants
def m1_lookahead_consumes_mobility_rng(impl: dict) -> dict:
    """M1 — the lookahead moves the users, i.e. consumes the mobility stream."""

    def geom(driver, candidates):
        driver._users.step(np.random.default_rng(0))
        return tn.next_step_geometry(driver, candidates)

    return {**impl, "geom": geom}


def m1b_lookahead_advances_the_environment(impl: dict) -> dict:
    """M1b — the most tempting wrong implementation: actually step the driver
    to read the real ``t+1`` candidate table."""

    def geom(driver, candidates):
        driver.step(np.random.default_rng(0))
        return tn.next_step_geometry(driver, candidates)

    return {**impl, "geom": geom}


def m2_slot_index_as_physical_identity(impl: dict) -> dict:
    """M2 — the forbidden approximation: the ``t+1`` geometry is read off slot
    *positions* rather than the associations they resolved to at ``t``.

    Modelled by rotating the satellite window one slot, which is exactly what
    raw slot persistence produces when the D2 margin ordering moves.
    """

    def geom(driver, candidates):
        rotated = copy.copy(candidates)
        object.__setattr__(
            rotated,
            "window_norad_ids",
            np.roll(np.asarray(candidates.window_norad_ids), 1, axis=1),
        )
        return tn.next_step_geometry(driver, rotated)

    return {**impl, "geom": geom}


def m3_lexicographic_order_permuted(impl: dict) -> dict:
    """M3 — terms 1 and 2 swapped: gain is consulted before persistence."""

    def rank(legal, persists, gain, score):
        indices = np.flatnonzero(np.asarray(legal, dtype=bool))
        if indices.size == 0:
            return NO_OP_ACTION
        keys = [
            (float(gain[a]), bool(persists[a]), float(score[a]), -int(a))
            for a in indices.tolist()
        ]
        return _pick(keys, persists, gain, score, indices)

    return {**impl, "rank": rank}


def m3b_t0_score_promoted(impl: dict) -> dict:
    """M3b — term 3 promoted above term 2, which quietly makes this T0."""

    def rank(legal, persists, gain, score):
        indices = np.flatnonzero(np.asarray(legal, dtype=bool))
        if indices.size == 0:
            return NO_OP_ACTION
        keys = [
            (bool(persists[a]), float(score[a]), float(gain[a]), -int(a))
            for a in indices.tolist()
        ]
        return _pick(keys, persists, gain, score, indices)

    return {**impl, "rank": rank}


def m4_final_step_not_t0(impl: dict) -> dict:
    """M4 — the final step keeps ranking on a stale lookahead instead of T0."""

    def act(states, masks, *, driver, candidates, is_final_step):
        return tn.tnext_actions(
            states, masks, driver=driver, candidates=candidates, is_final_step=False
        )

    return {**impl, "act": act}


def m4b_final_step_nondeterministic(impl: dict) -> dict:
    """M4b — the fallback is a random legal action rather than T0's."""
    counter = {"n": 0}

    def act(states, masks, *, driver, candidates, is_final_step):
        actions, diag, geometry = tn.tnext_actions(
            states,
            masks,
            driver=driver,
            candidates=candidates,
            is_final_step=is_final_step,
        )
        if is_final_step:
            counter["n"] += 1
            rng = np.random.default_rng(counter["n"])
            actions = np.asarray(actions).copy()
            for uid, mask in enumerate(masks):
                valid = np.flatnonzero(mask.mask)
                if valid.size:
                    actions[uid] = int(rng.choice(valid))
        return actions, diag, geometry

    return {**impl, "act": act}


def m5_illegal_action_enterable(impl: dict) -> dict:
    """M5 — the ranking searches all 28 slots instead of the legal ones."""

    def rank(legal, persists, gain, score):
        indices = np.arange(NUM_ACTIONS)
        keys = [
            tn.lexicographic_key(int(a), persists, gain, score)
            for a in indices.tolist()
        ]
        return _pick(keys, persists, gain, score, indices)

    return {**impl, "rank": rank}


def m6_ties_break_on_highest_index(impl: dict) -> dict:
    """M6 — term 4's sign flipped: ties go to the highest index."""

    def rank(legal, persists, gain, score):
        indices = np.flatnonzero(np.asarray(legal, dtype=bool))
        if indices.size == 0:
            return NO_OP_ACTION
        keys = [
            (bool(persists[a]), float(gain[a]), float(score[a]), int(a))
            for a in indices.tolist()
        ]
        return _pick(keys, persists, gain, score, indices)

    return {**impl, "rank": rank}


def m7_source_identity_absent_from_hash(impl: dict) -> dict:
    """M7 — the hashed payload drops the source identity."""

    def identity():
        payload = dict(tn.source_identity())
        for key in ("source_id", "source_version", "spec"):
            payload.pop(key, None)
        return payload

    return {**impl, "identity": identity}


def m8_lookahead_offset_zero(impl: dict) -> dict:
    """M8 — the lookahead reads the CURRENT step's ephemeris.

    Not in the required list, but it is the mutation that would make the whole
    source a current-step gain rule with every other check still green, so it
    gets a named mutant.
    """

    def geom(driver, candidates):
        original = driver.satellite_ecef_at
        driver.satellite_ecef_at = lambda offset: original(0)
        try:
            return tn.next_step_geometry(driver, candidates)
        finally:
            del driver.satellite_ecef_at

    return {**impl, "geom": geom}


def m9_gain_uses_stochastic_shadowing(impl: dict) -> dict:
    """M9 — the 'nominal' gain carries a shadow-fading draw, so the lookahead
    is no longer the deterministic budget §2A requires."""
    state = {"n": 0}

    def geom(driver, candidates):
        out = tn.next_step_geometry(driver, candidates)
        state["n"] += 1
        rng = np.random.default_rng(state["n"])
        noisy = out.nominal_gain * 10.0 ** (
            rng.normal(0.0, 2.0, size=out.nominal_gain.shape) / 10.0
        )
        return tn.NextStepGeometry(
            persists=out.persists,
            nominal_gain=noisy,
            off_axis_deg=out.off_axis_deg,
            slant_range_km=out.slant_range_km,
            elevation_deg=out.elevation_deg,
            cell_visible=out.cell_visible,
            user_visible=out.user_visible,
            identified=out.identified,
        )

    return {**impl, "geom": geom}


MUTANTS: dict[str, tuple[Callable, str]] = {
    "M1_lookahead_consumes_mobility_rng": (
        m1_lookahead_consumes_mobility_rng, "lookahead_is_side_effect_free"),
    "M1b_lookahead_advances_the_environment": (
        m1b_lookahead_advances_the_environment, "lookahead_is_side_effect_free"),
    "M2_slot_index_as_physical_identity": (
        m2_slot_index_as_physical_identity, "association_not_slot_identity"),
    "M3_lexicographic_order_permuted": (
        m3_lexicographic_order_permuted, "persistence_dominates_gain"),
    "M3b_t0_score_promoted": (m3b_t0_score_promoted, "gain_dominates_t0_score"),
    "M4_final_step_not_t0": (m4_final_step_not_t0, "final_step_is_t0"),
    "M4b_final_step_nondeterministic": (
        m4b_final_step_nondeterministic, "final_step_is_t0"),
    "M5_illegal_action_enterable": (
        m5_illegal_action_enterable, "illegal_action_is_unreachable"),
    "M6_ties_break_on_highest_index": (
        m6_ties_break_on_highest_index, "ties_break_on_lowest_index"),
    "M7_source_identity_absent_from_hash": (
        m7_source_identity_absent_from_hash, "source_identity_in_hash"),
    "M8_lookahead_offset_zero": (
        m8_lookahead_offset_zero, "lookahead_reads_the_next_step"),
    "M9_gain_uses_stochastic_shadowing": (
        m9_gain_uses_stochastic_shadowing, "lookahead_is_deterministic"),
}


def _run(name: str, impl: dict, live=None) -> None:
    check, _ = CHECKS[name]
    check(**impl, live=live)


# ------------------------------------------------------------------- green
@pytest.mark.parametrize("name", [n for n, (_, l) in CHECKS.items() if not l])
def test_check_green_pure(name):
    _run(name, _real())


@pytest.mark.parametrize("name", [n for n, (_, l) in CHECKS.items() if l])
def test_check_green_live(name, live):
    _run(name, _real(), live)


# --------------------------------------------------------------------- red
@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_mutant_is_red(name, request):
    mutate, target = MUTANTS[name]
    _, needs_live = CHECKS[target]
    live_obj = request.getfixturevalue("live") if needs_live else None
    with pytest.raises((AssertionError, MCRLContractError, KeyError, IndexError)):
        _run(target, mutate(_real()), live_obj)
