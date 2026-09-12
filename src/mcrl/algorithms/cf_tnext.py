"""``T_NEXT`` — the one-step temporal-foresight / association-persistence source.

Frozen prospectively in Amendment 15 §2A
(``.scratch/multi-catfish-v025-physics-successor/
V025-CONTROLLER-AMENDMENT-15-PARALLEL-CATFISH-PORTFOLIO-2026-09-12.md``,
commit ``e5809fdf``).  **Development lane only.**  Nothing computed here is
formal evidence, and this module never trains, never steps the environment and
never draws from a generator.

The source, verbatim from §2A.  For focal user ``u`` and each **currently
legal** action ``a`` at step ``t``:

1. resolve ``a`` to the underlying **stable physical satellite/beam
   association**;
2. inspect the **deterministic** geometry at ``t+1`` for the same user and the
   same physical association;
3. the lookahead is **side-effect-free**;
4. rank legal current actions **lexicographically** by

       ( same_physical_association_is_legal_or_visible_at_t_plus_1,
         nominal_next_step_link_gain_for_that_same_association,
         current_T0_score,
         -current_action_index )

At the final decision step it falls back deterministically to T0 and the
fallback is counted separately.

Three implementation facts that the report has to carry, because each of them
is a place where a plausible shortcut would measure something else.

**(a) The association is a real object in this code, not an approximation.**
``env/action_contract.py`` states the rule in its own module docstring —
"handover is decided from the REALISED ASSOCIATION (norad_id, cell_id), never
from the action index" (§4A.4) — and ``SlotTable.association(a)`` returns
exactly that pair.  ``StepCandidates`` carries ``window_norad_ids`` ``(U, L)``
("stable slot identities") and ``dwell.neighborhood_cell_ids`` ``(U, J)``,
whose product under ``a = 7·l + j`` is the ``(28,)`` pair of identity arrays on
``SlotTable``.  NORAD ids are catalogue identities and cell ids index an
earth-fixed lattice, so both are stable across steps while the *slot* is not.
§2A's prohibition on raw slot persistence is therefore avoidable, and it is
avoided: the ``t+1`` geometry below is built from the identities read at ``t``
and never from whatever occupies slot ``a`` at ``t+1``.

**(b) Only the ephemeris may advance.** ``ScenarioDriver.satellite_ecef_at``
propagates the tracked set to any decision-step offset from ``_start_utc`` and
``_step_index``; it mutates nothing and draws nothing (it already serves the
``τ`` warm start at *negative* offsets).  User mobility is the opposite:
``RandomWanderingUsers.step`` draws a bounded turn from the mobility
generator, so a user's ``t+1`` position does not exist without consuming that
generator, which §2A clause 3 forbids.  The users are therefore held at their
``t`` positions — which is precisely "the **deterministic** geometry at
``t+1``".  At ``Δt = 30.08 s`` a satellite moves ≈ 226 km and a 30 km/h user
moves 251 m, so what is held fixed is also the small term, but the reason it
is held fixed is the prohibition, not the size.

**(c) "Legal or visible" is evaluated on the disjunct that is computable
side-effect-free.** The mask is an AND of three terms (``candidates.py``):
slot occupied (D2 eligibility), cell exists (the dwell neighbourhood), cell
reachable (the satellite is above the cell's horizon).  The first two are
functions of latched D2 counters and of the dwell re-key schedule, and
advancing either is a state mutation.  The third is pure geometry.  So the
``t+1`` term is the geometric disjunct: the same satellite is above the same
cell's horizon **and** above the focal user's horizon at ``t+1``, both at the
project's own existing 0° thresholds (``CELL_VISIBILITY_MIN_ELEVATION_DEG``,
``ScenarioConfig.screen_min_elevation_deg``).  No new constant is introduced.

The gain is the project's frozen deterministic link budget with the two
stochastic terms absent: ``G_T(θ) · H`` with ``fading_gain=None`` and
``shadow_fading_db=0``, which ``link_budget.total_path_loss_db`` itself calls
"the deterministic budget".  The constant ``p⁰`` is a positive scalar common
to every candidate and is omitted because it cannot change a ranking.  No
target SINR, no ACM threshold, no ``R_min``, no power controller: rulings C-2,
PATCH P-22 and Amendment 11 are respected by construction, since nothing here
inverts a rate onto a power.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..env.action_contract import (
    NO_OP_ACTION,
    NUM_ACTIONS,
    NUM_BEAM_SLOTS,
    NUM_SATELLITE_SLOTS,
    no_op_actions,
)
from ..env.antenna import RX_GAIN_MAX_DBI, transmit_gain_linear
from ..env.candidates import CELL_VISIBILITY_MIN_ELEVATION_DEG, _cell_visibility
from ..env.link_budget import link_power_factor
from ..env.pointing import candidate_geometry
from ..errors import MCRLContractError
from .cf_teacher import t0_scores

SOURCE_ID: str = "T_NEXT"
SOURCE_VERSION: str = "assoc-persistence-lookahead-v1"
SOURCE_SPEC: str = "V025-CONTROLLER-AMENDMENT-15 section 2A"

_RX_GAIN_MAX_LINEAR: float = 10.0 ** (RX_GAIN_MAX_DBI / 10.0)
"""Identical to ``env/step.py``'s module-level constant of the same name."""


def source_identity() -> dict[str, object]:
    """Canonical identity of this source, for the configuration hash.

    Amendment 15 §6 requires the config hash to contain canonical teacher
    identities.  The mutant ``M7`` removes this from the hashed payload.
    """
    return {
        "source_id": SOURCE_ID,
        "source_version": SOURCE_VERSION,
        "spec": SOURCE_SPEC,
        "criteria": (
            "lexicographic("
            "same_physical_association_legal_or_visible_at_t_plus_1, "
            "nominal_next_step_link_gain, current_T0_score, -action_index)"
        ),
        "association": "(norad_id, cell_id) via SlotTable.association",
        "lookahead": "ScenarioDriver.satellite_ecef_at(+1); users held at t",
        "gain": "transmit_gain_linear(theta) * link_power_factor(slant, elev, G_R) "
        "with fading_gain=None and shadow_fading_db=0",
        "visibility_thresholds_deg": {
            "cell": CELL_VISIBILITY_MIN_ELEVATION_DEG,
            "user": "ScenarioConfig.screen_min_elevation_deg",
        },
        "final_step": "deterministic T0 fallback, counted separately",
    }


# --------------------------------------------------------------- lookahead
@dataclass(frozen=True)
class NextStepGeometry:
    """The deterministic ``t+1`` geometry of the ``t`` associations.

    Every array is ``(U, 28)`` in the ``a = 7·l + j`` layout, carrying the
    association read at ``t`` forward — **not** slot ``a`` of the ``t+1``
    candidate table, which does not exist yet and is not what §2A asks for.
    """

    persists: np.ndarray
    """bool — the same ``(norad, cell)`` pair is visible at ``t+1``."""
    nominal_gain: np.ndarray
    """float64 — ``G_T(θ)·H`` of that same association at ``t+1``."""
    off_axis_deg: np.ndarray
    slant_range_km: np.ndarray
    elevation_deg: np.ndarray
    cell_visible: np.ndarray
    """bool — the satellite is above the CELL's horizon at ``t+1``."""
    user_visible: np.ndarray
    """bool — the satellite is above the USER's horizon at ``t+1``."""
    identified: np.ndarray
    """bool — the slot carried a resolvable ``(norad, cell)`` pair at ``t``."""


def next_step_geometry(driver, candidates) -> NextStepGeometry:
    """Deterministic ``t+1`` geometry of every ``t`` association.

    Side-effect-free by construction: it reads ``driver``'s satellites, epoch
    and step index, propagates the ephemeris with
    :meth:`ScenarioDriver.satellite_ecef_at`, and holds the users where they
    are.  No generator is touched, no attribute is written, nothing is stepped.
    ``tests/test_cf_tnext.py::test_lookahead_is_side_effect_free`` pins that as
    bit-identical RNG and environment state across a call.
    """
    users = int(candidates.window_norad_ids.shape[0])
    norads = np.asarray(candidates.window_norad_ids, dtype=np.int64)
    if norads.shape != (users, NUM_SATELLITE_SLOTS):
        raise MCRLContractError("window_norad_ids must be (U, L)")

    positions = driver.satellite_ecef_at(1)
    window_next = np.full((users, NUM_SATELLITE_SLOTS, 3), np.nan, dtype=np.float64)
    for uid in range(users):
        for slot in range(NUM_SATELLITE_SLOTS):
            norad = int(norads[uid, slot])
            if norad < 0:
                continue
            if norad not in positions:
                raise MCRLContractError(
                    f"NORAD {norad} occupies a slot but is not in the tracked set"
                )
            window_next[uid, slot] = positions[norad]

    user_ecef = driver.user_ecef_km()
    cells = np.asarray(candidates.dwell.neighborhood_cell_ids, dtype=np.int64)
    grid = driver.grid

    # Same placeholder discipline as ``candidates.resolve_candidates``: an
    # unoccupied slot needs *a* finite position so the broadcast arccos stays
    # clean, and is masked out afterwards.
    anchor = next(iter(positions.values()))
    geometry_input = np.where(np.isnan(window_next), anchor[None, None, :], window_next)
    geometry = candidate_geometry(
        user_ecef_km=user_ecef,
        satellite_ecef_km=geometry_input,
        cell_centres_ecef_km=grid.centers_ecef_km,
        neighborhood_cell_ids=cells,
    )
    reachable = _cell_visibility(
        grid=grid,
        neighborhood_cell_ids=cells,
        window_satellite_ecef_km=window_next,
        min_elevation_deg=CELL_VISIBILITY_MIN_ELEVATION_DEG,
    )

    def _flat_lj(block: np.ndarray) -> np.ndarray:
        """``(U, L, J)`` -> ``(U, 28)`` in the ``a = 7·l + j`` layout."""
        return np.asarray(block).reshape(block.shape[0], NUM_ACTIONS)

    def _flat_l(block: np.ndarray) -> np.ndarray:
        """``(U, L)`` -> ``(U, 28)``: a per-satellite value, repeated over J."""
        return np.repeat(np.asarray(block), NUM_BEAM_SLOTS, axis=1)

    theta = _flat_lj(geometry.off_axis_deg)
    slant = _flat_l(geometry.slant_range_km)
    elevation = _flat_l(geometry.elevation_deg)
    cell_visible = _flat_lj(reachable)
    # ``a = 7·l + j``: the satellite predicate repeats over j, the cell
    # predicate tiles over l.  Getting these two the wrong way round is the
    # classic 28-slot indexing bug, so they are written as different calls.
    identified = _flat_l(norads >= 0) & np.tile(cells >= 0, (1, NUM_SATELLITE_SLOTS))

    min_user_elevation = float(
        getattr(driver.config, "screen_min_elevation_deg", 0.0)
    )
    user_visible = elevation >= min_user_elevation

    finite = np.isfinite(theta) & np.isfinite(slant) & np.isfinite(elevation)
    usable = identified & finite
    safe_theta = np.where(usable, theta, 0.0)
    safe_slant = np.where(usable, slant, 1.0)
    safe_elevation = np.where(usable, elevation, 0.0)
    gain = transmit_gain_linear(safe_theta) * link_power_factor(
        safe_slant,
        safe_elevation,
        np.full(safe_slant.shape, _RX_GAIN_MAX_LINEAR),
    )
    gain = np.where(usable, gain, 0.0)

    persists = usable & cell_visible & user_visible
    return NextStepGeometry(
        persists=persists,
        nominal_gain=gain,
        off_axis_deg=theta,
        slant_range_km=slant,
        elevation_deg=elevation,
        cell_visible=cell_visible & usable,
        user_visible=user_visible & usable,
        identified=identified,
    )


# ------------------------------------------------------------------ ranking
def lexicographic_key(
    action: int, persists: np.ndarray, gain: np.ndarray, t0_score: np.ndarray
) -> tuple[bool, float, float, int]:
    """§2A clause 4's key, in its declared order.

    ``-action`` last means the lowest index wins a full tie, which is the
    project's own "first index on ties" convention (``cf_teacher.t0_scores``,
    ``masked_argmax_rows``).
    """
    return (
        bool(persists[action]),
        float(gain[action]),
        float(t0_score[action]),
        -int(action),
    )


def rank_legal_actions(
    legal: np.ndarray, persists: np.ndarray, gain: np.ndarray, t0_score: np.ndarray
) -> int:
    """The single highest-ranked legal action, or ``NO_OP_ACTION`` if none."""
    indices = np.flatnonzero(np.asarray(legal, dtype=bool))
    if indices.size == 0:
        return NO_OP_ACTION
    best = int(indices[0])
    best_key = lexicographic_key(best, persists, gain, t0_score)
    for action in indices[1:].tolist():
        key = lexicographic_key(int(action), persists, gain, t0_score)
        if key > best_key:
            best, best_key = int(action), key
    return best


# ------------------------------------------------------------------ source
def tnext_actions(
    states,
    masks,
    *,
    driver,
    candidates,
    is_final_step: bool,
):
    """``T_NEXT``'s action for every user, plus the per-step diagnostics.

    ``is_final_step`` is the caller's assertion that no ``t+1`` exists inside
    the episode.  It is the caller's because the episode length lives on the
    scenario config, not on the driver's per-step state, and passing it makes
    the fallback testable without a terminal episode.
    """
    users = len(states)
    scores, t0_acts, legal_mask = t0_scores(states, masks)
    actions = np.asarray(no_op_actions(users), dtype=np.int64)

    diag = {
        "decisions": 0,
        "fallback_final_step": 0,
        "no_legal_action": 0,
        "persist_true": 0,
        "persist_false": 0,
        "criterion_active": 0,
        "criterion_decisive": 0,
        "agree_t0": 0,
    }

    if is_final_step:
        # §2A: "fall back deterministically to T0".  T0 is already the
        # deterministic masked argmax with first-index tie-breaking, so the
        # fallback is literally T0's action, not a re-derivation of it.
        for uid in range(users):
            if not bool(legal_mask[uid].any()):
                diag["no_legal_action"] += 1
                continue
            diag["decisions"] += 1
            diag["fallback_final_step"] += 1
            actions[uid] = int(t0_acts[uid])
            diag["agree_t0"] += 1
        return actions, diag, None

    geometry = next_step_geometry(driver, candidates)

    for uid in range(users):
        legal = np.flatnonzero(legal_mask[uid])
        if legal.size == 0:
            diag["no_legal_action"] += 1
            continue
        diag["decisions"] += 1

        persists = geometry.persists[uid]
        gain = geometry.nominal_gain[uid]
        score = scores[uid]

        best = rank_legal_actions(legal_mask[uid], persists, gain, score)
        if best == NO_OP_ACTION or not bool(legal_mask[uid][best]):
            raise MCRLContractError(
                f"T_NEXT selected action {best}, which is illegal for user {uid}"
            )
        actions[uid] = best

        flags = persists[legal]
        n_true = int(np.count_nonzero(flags))
        diag["persist_true"] += n_true
        diag["persist_false"] += int(flags.size - n_true)
        if 0 < n_true < flags.size:
            # The visibility term separates at least one legal action from at
            # least one other, so it is capable of deciding this state.
            diag["criterion_active"] += 1
            # It is *decisive* when dropping it would change the action.
            without = int(legal[0])
            without_key = (float(gain[without]), float(score[without]), -without)
            for action in legal[1:].tolist():
                key = (float(gain[action]), float(score[action]), -int(action))
                if key > without_key:
                    without, without_key = int(action), key
            if without != best:
                diag["criterion_decisive"] += 1
        diag["agree_t0"] += int(best == int(t0_acts[uid]))

    return actions, diag, geometry


def tnext_policy(*, env, steps_per_episode: int):
    """``T_NEXT`` as a ``pooled_rollout``-shaped policy over a live ``env``.

    The policy needs more than the 113-dim observation — it needs the slot
    tables and the ephemeris — so it is **privileged** by the Stage-0
    condition-1 sense of the word, which is exactly why Amendment 15 §5
    requires the ``A_repr`` probe before any learner run.
    """
    state = {"t": 0, "diag": [], "observation": None}

    def policy(enc, masks, states):
        observation = state["observation"]
        if observation is None:
            raise MCRLContractError("bind the step-0 observation before acting")
        actions, diag, _ = tnext_actions(
            states,
            masks,
            driver=env.environment.driver,
            candidates=observation.candidates,
            is_final_step=(state["t"] >= int(steps_per_episode) - 1),
        )
        state["diag"].append(diag)
        state["t"] += 1
        return actions

    policy.state = state  # type: ignore[attr-defined]
    return policy
