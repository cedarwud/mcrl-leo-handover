"""Probe P3 — does the counting-form ``r3`` discriminate, and at what scale?

Two questions in one probe because they share one measurement.

**SDD §4's P3 (B17 Q3): does ``r3`` discriminate at all?**  ``r3,u = −U_{b_u}``
is only informative if a user's 28 candidates *differ* in load.  If every
candidate names an equally busy beam, ``r3`` returns the same number
whatever the user does, and the third objective cannot steer.  SDD asks for
the **width of the ``U_{b_u}`` distribution across one user's 28 candidates**
and the **per-decision argmax agreement with ``r1``** — if the two objectives
always prefer the same candidate, the multi-objective problem is degenerate
in a way no weight vector can fix.

**Q-D: what scale does ``r3`` enter training at?**  B13 changed its units
from a normalised gap to a raw user count, so the inherited scale means
nothing for it.  The frozen selection mapping is "the p95 of ``|r3|`` over
served steps, rounded to the nearest integer" — this probe supplies that
number and **does not choose it**; the rule was committed first.

**The counterfactual is done properly, not naively.**  Asking "what would
``r3`` be if user ``u`` took candidate ``c``" is not "the load of ``c``'s
beam": ``u`` would *join* that beam, so the load they would experience is
the load **excluding themselves** plus one.  Reading the realised load
straight off would credit a user who is already on that beam with a load
one lower than everyone else on it, and the argmax would tilt toward
staying put for an arithmetic reason rather than a load one.

**Three generators, and the signature says so.**  ``env_rng`` (fading),
``mobility_rng`` (users) and ``action_rng`` (the policy) are separate
parameters rather than one ``rng``, because P3 is read alongside ablation
probes that share this module's conventions and one shared stream makes an
ablation measure the wrong thing (``PROBE_RNG_POLICY``).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import numpy as np

from ..env.action_contract import NO_OP_ACTION, NUM_ACTIONS
from ..env.link_budget import shannon_rate_bps
from ..env.reference_policy import ReferencePolicyRunner
from ..env.step import StepEnvironment, StepObservation, StepOutcome
from ..errors import MCRLContractError
from .prereg import PreregRecord, assert_data_blind


@dataclass
class P3Accumulator:
    """Running tallies for one P3 run."""

    decision_steps: int = 0
    candidate_load_width: list[float] = field(default_factory=list)
    """``max − min`` of ``U_{b_u}`` across a user's 28 candidates."""
    candidate_load_distinct: list[int] = field(default_factory=list)
    """How many distinct load values those 28 candidates offer."""
    argmax_agreements: int = 0
    """Strict: ``argmax(r1) == argmax(r3)``, both first-index tie-broken."""
    setwise_agreements: int = 0
    """Loose: ``argmax(r1)`` lands anywhere in ``r3``'s best set."""
    argmax_comparisons: int = 0
    r3_best_set_size: list[float] = field(default_factory=list)
    strict_null: list[float] = field(default_factory=list)
    setwise_null: list[float] = field(default_factory=list)
    realised_abs_r3: list[float] = field(default_factory=list)
    realised_r1: list[float] = field(default_factory=list)
    r1_values: list[float] = field(default_factory=list)
    r2_values: list[float] = field(default_factory=list)
    r3_values: list[float] = field(default_factory=list)
    step_r1_mean: list[float] = field(default_factory=list)
    step_r3_mean: list[float] = field(default_factory=list)

    def observe(
        self,
        observation: StepObservation,
        outcome: StepOutcome,
        *,
        beam_bandwidth_hz: float,
    ) -> None:
        """Tally one step from the observation it was chosen against."""
        resolution = outcome.resolution
        users = len(observation.user_states)
        self.decision_steps += users

        rewards = outcome.reward_matrix
        self.r1_values.extend(rewards[:, 0].tolist())
        self.r2_values.extend(rewards[:, 1].tolist())
        self.r3_values.extend(rewards[:, 2].tolist())
        self.step_r1_mean.append(float(rewards[:, 0].mean()))
        self.step_r3_mean.append(float(rewards[:, 2].mean()))

        served = resolution.served
        if np.any(served):
            self.realised_r1.extend(rewards[served, 0].tolist())
            self.realised_abs_r3.extend(
                np.abs(rewards[served, 2]).tolist()
            )

        power = outcome.system_power_w
        for uid in range(users):
            table = observation.candidates.slot_tables[uid]
            valid = np.flatnonzero(table.mask)
            if valid.size < 2:
                # One candidate cannot be "discriminated" between.
                continue

            loads = _counterfactual_loads(uid, table, valid, outcome)
            self.candidate_load_width.append(float(loads.max() - loads.min()))
            self.candidate_load_distinct.append(int(np.unique(loads).size))

            if power <= 0.0:
                continue
            sinr = observation.candidate_sinr[uid, valid]
            rate = shannon_rate_bps(
                np.maximum(sinr, 0.0),
                beam_load=loads,
                bandwidth_hz=beam_bandwidth_hz,
            )
            r1_candidates = rate / power
            r3_candidates = -loads

            # ⚠ Two agreement metrics with two different null rates, because
            # r3 TIES heavily: a user's 28 candidates take only ~4 distinct
            # load values, so r3's "best" is usually a SET, not a candidate.
            #
            # Comparing a strict argmax==argmax rate against a set-membership
            # null (|best set| / n) mixes the two up and can make a result
            # 2.7x above chance look like chance.  Both are reported with
            # their own null.
            best = np.flatnonzero(r3_candidates == r3_candidates.max())
            pick = int(np.argmax(r1_candidates))
            self.argmax_comparisons += 1
            if pick == int(np.argmax(r3_candidates)):
                self.argmax_agreements += 1
            if pick in set(best.tolist()):
                self.setwise_agreements += 1
            self.r3_best_set_size.append(float(best.size))
            # Null model: r1's preference independent of r3's and uniform
            # over the valid candidates.  Stated rather than assumed --
            # it is what makes the ratios below interpretable.
            self.strict_null.append(1.0 / valid.size)
            self.setwise_null.append(best.size / valid.size)

    def summarise(self) -> dict[str, object]:
        width = np.array(self.candidate_load_width, dtype=np.float64)
        distinct = np.array(self.candidate_load_distinct, dtype=np.float64)
        served_r1 = np.array(self.realised_r1, dtype=np.float64)
        abs_r3 = np.array(self.realised_abs_r3, dtype=np.float64)
        r1 = np.array(self.r1_values, dtype=np.float64)
        r2 = np.array(self.r2_values, dtype=np.float64)
        r3 = np.array(self.r3_values, dtype=np.float64)

        scale = _qd_scale(abs_r3)
        return {
            "probe": "P3",
            "decision_steps": self.decision_steps,
            # -- SDD's B17 Q3: does r3 discriminate? --------------------
            "candidate_load_width": _quantiles(width),
            "candidate_load_distinct_values": _quantiles(distinct),
            "degenerate_step_fraction": (
                float(np.mean(width == 0.0)) if width.size else 0.0
            ),
            "argmax_comparisons": self.argmax_comparisons,
            "r1_r3_argmax_agreement": _agreement(
                self.argmax_agreements, self.argmax_comparisons, self.strict_null
            ),
            "r1_r3_setwise_agreement": _agreement(
                self.setwise_agreements, self.argmax_comparisons, self.setwise_null
            ),
            "r3_best_set_size": _quantiles(
                np.array(self.r3_best_set_size, dtype=np.float64)
            ),
            "argmax_tie_break": (
                "first index in slot order (satellite-major, beam-minor); "
                "r3 ties heavily, so the strict metric compares against ONE "
                "member of the best set and its null is 1/n, not |best|/n"
            ),
            # -- Q-D: the scale -----------------------------------------
            "abs_r3_over_served_steps": _quantiles(abs_r3),
            "qd_scale_p95_rounded": scale,
            # -- magnitudes and separability ----------------------------
            # ``r1`` remains the all-decision descriptive series.  The
            # calibration mapping explicitly says served steps, so its input
            # is reported separately and must never be inferred from this one.
            "r1_over_served_steps": _quantiles(served_r1),
            "r1": _quantiles(r1),
            "r2": _quantiles(r2),
            "r3": _quantiles(r3),
            "r1_r3_step_correlation": _correlation(
                np.array(self.step_r1_mean), np.array(self.step_r3_mean)
            ),
        }


def _counterfactual_loads(
    uid: int,
    table,
    valid: np.ndarray,
    outcome: StepOutcome,
) -> np.ndarray:
    """``U`` this user would experience on each valid candidate.

    The load **excluding this user**, plus one for joining.  A user already
    on a beam must not be credited with a lower load than the strangers
    beside them — that would make the argmax prefer staying put for an
    arithmetic reason rather than a congestion one.
    """
    resolution = outcome.resolution
    here = (
        int(resolution.serving_satellite[uid]),
        int(resolution.serving_cell[uid]),
    ) if resolution.served[uid] else None

    loads = np.empty(valid.size, dtype=np.float64)
    for index, action in enumerate(valid.tolist()):
        beam = (int(table.norad_ids[action]), int(table.cell_ids[action]))
        occupied = resolution.eligible_load_by_beam.get(beam, 0)
        if beam == here:
            occupied -= 1
        loads[index] = occupied + 1
    return loads


def _qd_scale(abs_r3: np.ndarray) -> int:
    """The frozen Q-D mapping, applied — **not chosen** here.

    "p95 of ``|r3|`` over served steps, rounded to the nearest integer."
    p95 rather than max because the max is one congested beam and would
    make the divisor a function of a single outlier; the integer keeps it a
    countable quantity rather than a fitted one.
    """
    if abs_r3.size == 0:
        raise MCRLContractError(
            "no served step produced an r3 value; the Q-D mapping has "
            "nothing to apply and a scale must not be invented"
        )
    return int(round(float(np.percentile(abs_r3, 95))))


def _agreement(
    hits: int, comparisons: int, null: Sequence[float]
) -> dict[str, float | None]:
    """An agreement rate is uninterpretable without its null.

    Reported as a ratio to chance, because the raw rate answers the wrong
    question: the interesting comparison is against RANDOM agreement, not
    against 100%.  A ratio near 1 means the metric shows nothing either
    way — neither coupling nor separation.
    """
    if comparisons == 0:
        return {"rate": None, "null": None, "ratio_to_chance": None}
    rate = hits / comparisons
    expected = float(np.mean(null)) if len(null) else 0.0
    return {
        "rate": rate,
        "null": expected,
        "ratio_to_chance": (rate / expected) if expected > 0.0 else None,
        "comparisons": float(comparisons),
    }


def _quantiles(values: np.ndarray) -> dict[str, float]:
    if values.size == 0:
        return {"count": 0.0}
    return {
        "count": float(values.size),
        "min": float(values.min()),
        "p05": float(np.percentile(values, 5)),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": float(values.max()),
        "mean": float(values.mean()),
    }


def _correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    """Pearson ``r`` between two per-step series, or ``None`` if undefined.

    ``None`` rather than 0.0 when a series is constant: a correlation that
    does not exist and a correlation that is zero are different findings,
    and F-2's defect would have shown up as the second.
    """
    if left.size < 2 or right.size < 2:
        return None
    if float(left.std()) == 0.0 or float(right.std()) == 0.0:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def run_probe_p3(
    *,
    prereg: PreregRecord,
    policy: ReferencePolicyRunner,
    environment: StepEnvironment,
    epochs: Sequence[dt.datetime],
    env_rng: np.random.Generator,
    mobility_rng: np.random.Generator,
    action_rng: np.random.Generator,
) -> dict[str, object]:
    """Drive a data-blind policy over the frozen scenario and tally P3.

    ``prereg`` is verified and its probe grid checked, the same as P1: a
    probe that could run before the freeze would make "the mapping was
    committed in advance" an honour system.
    """
    prereg.verify()
    assert_data_blind(policy=policy.declaration)
    grid = prereg.sections.get("probe_grid", {})
    if not grid.get("P3"):
        raise MCRLContractError(
            "the frozen PREREG has no P3 entry in its probe grid; §7.1 "
            "requires the complete grid to be frozen before the first probe"
        )
    mapping = prereg.sections.get("selection_mappings", {}).get(
        "Q-D r3 calibration scale"
    )
    if not mapping:
        raise MCRLContractError(
            "P3 closes Q-D, so its selection mapping must be in the frozen "
            "record before P3 runs -- otherwise the scale is chosen after "
            "seeing the numbers, which is the leak §7.1 names"
        )

    accumulator = P3Accumulator()
    bandwidth = environment.physics.beam_bandwidth_hz
    for epoch in epochs:
        observation = environment.reset(
            epoch, env_rng, mobility_rng=mobility_rng
        )
        policy.reset()
        while True:
            actions = policy.act(observation.candidates, action_rng)
            outcome = environment.step(actions, env_rng)
            accumulator.observe(
                observation, outcome, beam_bandwidth_hz=bandwidth
            )
            observation = outcome.observation
            if outcome.done:
                break

    if accumulator.decision_steps == 0:
        raise MCRLContractError("the probe consumed no steps")

    return {
        "prereg_digest": prereg.digest,
        "policy": policy.declaration.as_dict(),
        "epochs": [epoch.isoformat() for epoch in epochs],
        "selection_mapping": mapping,
    } | accumulator.summarise()


def apply_qd_scale(result: dict[str, object]) -> int:
    """Read the scale the frozen mapping selected out of a P3 result.

    Separate from :func:`run_probe_p3` so that closing Q-D is an explicit
    act with a visible input, rather than something a probe run does to the
    codebase as a side effect.
    """
    scale = result.get("qd_scale_p95_rounded")
    if not isinstance(scale, int) or scale < 1:
        raise MCRLContractError(
            f"P3 did not produce a usable Q-D scale (got {scale!r})"
        )
    return scale
