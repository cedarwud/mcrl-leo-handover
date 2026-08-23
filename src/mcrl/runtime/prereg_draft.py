"""The §7.1 pre-registration content, as code awaiting sign-off.

Everything derivable from the implementation is derived —
:func:`~mcrl.runtime.prereg.build_prereg_sections` reads the frozen
constants back out of the modules that own them, so the document cannot
drift from the code.  What is left is the part that exists *only* because
it is pre-registered: the probe grid, the thresholds, the stopping rules,
the deterministic selection mappings, the reference policy and its seed,
and the hold-out commitment.

**This module is the draft, not the freeze.**  Nothing here is sealed until
:func:`freeze` is called, and that is deliberate: §7.1's whole value is that
these choices were committed *before* the probes ran, so a value chosen —
or revised — after seeing probe output is the leak, not a correction.  Every
entry therefore carries the reasoning that would otherwise be invented
afterwards.

Two of the entries are not values at all.  Q-D and Q-E are outputs of probes
P3 and P2, so requiring their answers before the probes would be circular.
§7.1 accepts "門檻**或**決定性的選取映射" for exactly this case, and what is
frozen is the **rule that will turn the probe's output into the decision**.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from ..env.dwell import DWELL_N_CANDIDATES
from ..env.ephemeris import (
    TRAIN,
    BlockAlternatingSplit,
    EphemerisConfig,
    EpisodeStartSampler,
    build_freeze_manifest,
)
from ..env.tle import MAX_MALFORMED_RECORD_FRACTION
from .outage_gate import OUTAGE_RATE_NEGLIGIBLE_DEFAULT
from .prereg import (
    PreregRecord,
    ReferencePolicy,
    build_prereg_sections,
    freeze_prereg,
)

# ---------------------------------------------------------------------------
# The probe grid (SDD §4)
# ---------------------------------------------------------------------------
#
# ⚠ **Every number here was cross-checked against SDD §4's own table on
# 2026-08-23, and four of the six had drifted.**  The controller caught P5;
# checking the rest the same way turned up three more, all the same shape —
# a probe number carrying an obligation the PREREG had quietly dropped:
#
#   P5  taken over completely.  SDD's P5 is the receive-angle distribution
#       against S.465's theta^R_min, which discharges (3.10c)'s ANGULAR
#       applicability disclosure.  The action-set-contraction probe that had
#       taken the slot is real and stays -- as P7.
#   P3  narrowed.  SDD's P3 is B17 Q3, "does the new r3 discriminate?",
#       measured as the width of U_{b_u} across one user's 28 candidates AND
#       the per-decision argmax agreement with r1.  The PREREG had it as the
#       Q-D scale only; the argmax-agreement measurement had no owner.
#   P2  narrowed.  SDD asks for the P^N swing amplitude and the angle-aware
#       EE dynamic range per N.  Both were dropped when P2 was rebased from
#       "closes Q-E" to "sensitivity" -- but Q-E closing elsewhere does not
#       discharge P2's measurements.
#   P6  narrowed.  SDD's r2 revision adds a random-tie-break control arm,
#       perturbation stability, and cross-seed ranking consistency.  None
#       had an owner.
#
# The lesson is the controller's: check that a number is vacant before
# reusing it, and check that a number you keep still carries what it did.

PROBE_GRID: dict[str, Any] = {
    "P1": {
        "question": "Q-A/Q-B: visibility and D2 event rate under a fixed policy",
        "sdd_definition": (
            "per-step visible-satellite distribution, handover event rate, "
            "elevation and angular-rate distributions"
        ),
        "measures": [
            "D2-eligible satellites per user per step",
            "valid actions per user per step, and the starvation rate",
            "handover events split phi1 / phi2 / re-entry, from realised "
            "associations and never from indices",
            "elevation and its rate of change",
            "outage_infeasible rate -- the §4A.5a(4) input",
        ],
        "policy": "all three reference policies, reported separately",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": ["Q-A", "Q-B"],
        "ablation_dimension": None,
        "implemented": "runtime/probe_p1.py",
    },
    "P2": {
        "question": "sensitivity of the results to the dwell length N",
        "sdd_definition": (
            "P^N swing amplitude and angle-aware EE dynamic range for each "
            "N in {2,3,4}"
        ),
        "sweep": {"dwell_steps": list(DWELL_N_CANDIDATES)},
        "measures": [
            "P^N swing amplitude per N  (SDD, restored)",
            "angle-aware EE dynamic range per N  (SDD, restored)",
            "re-key rate and the fraction of re-keys that move j = 0",
            "handover rate attributable to re-keying rather than to geometry",
            "the headline metrics under each N, as a sensitivity band",
        ],
        "policy": "stay-if-possible",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "ablation_dimension": "dwell_steps",
        "note": (
            "Q-E is already closed at N = 3: the frozen mapping needs only "
            "the re-key rate, which is scenario characterisation available "
            "before any policy is evaluated.  P2 therefore reports "
            "sensitivity rather than making the choice -- but Q-E closing "
            "elsewhere does NOT discharge the two measurements SDD §4 asks "
            "P2 for, so they are restored above."
        ),
    },
    "P3": {
        "question": (
            "B17 Q3: does the counting-form r3 discriminate?  And Q-D: what "
            "scale does it enter training at?"
        ),
        "sdd_definition": (
            "width of the U_{b_u} distribution across one user's 28 "
            "candidate actions; per-decision argmax agreement rate with r1"
        ),
        "measures": [
            "width of U_{b_u} across a user's 28 candidates  (SDD, restored)",
            "per-decision argmax agreement between r1 and r3  (SDD, restored)",
            "distribution of realised U_{b_u} across the population",
            "p95 of |r3| over served steps -- the Q-D selection mapping's input",
            "|r1|, |r2|, |r3| magnitudes on the same steps",
            "correlation between r1 and r3 across steps -- they must be "
            "separable, which is what F-2's per-link power sum destroyed",
        ],
        "policy": "all three reference policies",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": ["Q-D", "B17-Q3"],
        "ablation_dimension": None,
        "note": (
            "the two questions share one measurement -- the U_{b_u} "
            "distribution -- which is why they can sit in one probe; but the "
            "argmax-agreement half is SDD's and was missing."
        ),
    },
    "P4": {
        "question": "does the interference model bind?  which term dominates?",
        "measures": [
            "I^intra / I^inter split per served link",
            "SINR distribution with and without the co-colour sum",
            "how often two satellites illuminate one cell -- (3.12b)'s v' = v",
        ],
        "policy": "all three reference policies",
        "episodes": 100,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "ablation_dimension": "co_colour_interference_enabled",
        "note": (
            "⚠ SDD §4 retired the OLD P4 series at r5 (dispersion-vs-EE, the "
            "EE-optimal beam count, the source of the 3.9x) as post-baseline "
            "ANALYSIS questions.  The number is genuinely vacant and is "
            "reused here with the controller's approval -- but this probe is "
            "UNRELATED to those, and saying so is the point of this note."
        ),
    },
    "P5": {
        "question": (
            "receive-angle distribution against S.465-6's theta^R_min -- "
            "does the envelope get evaluated where it is defined?"
        ),
        "sdd_definition": (
            "fraction of link evaluations falling at theta^R < 2.05 deg"
        ),
        "measures": [
            "distribution of the at-user inter-satellite separation angle "
            "over every interference term evaluated",
            "fraction of evaluations below theta^R_min",
            "how much received interference power those evaluations carry -- "
            "a rare-but-dominant tail reads differently from a rare-and-"
            "negligible one",
        ],
        "policy": "all three reference policies",
        "episodes": 100,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "ablation_dimension": None,
        "discharges": "eq. (3.10c)'s ANGULAR applicability disclosure",
        "note": (
            "⚠ RESTORED 2026-08-23.  This probe had been displaced by the "
            "action-set-contraction probe, which now holds P7.  ch3 "
            "currently discloses only (3.10c)'s FREQUENCY range (2-31 GHz "
            "per ITU-R S.465-6) and says nothing about its angular range, "
            "so this obligation had no owner at all.  ⚠ And "
            "``theta^R_min`` does not yet exist in env/antenna.py -- the "
            "restored probe exposes a missing constant, not just a missing "
            "measurement."
        ),
    },
    "P6": {
        "question": "the learning-rate sweep (ruling C-13)",
        "sdd_definition": (
            "alpha in {0.01, 0.003, 0.001} over short runs; report all four "
            "G-3 collapse metrics with q_margin NORMALISED; plus an r2 "
            "control arm that breaks near-ties at random, perturbation "
            "stability, and cross-seed ranking consistency"
        ),
        "sweep": {"learning_rate": [0.01, 0.003, 0.001]},
        "measures": [
            "q_margin, NORMALISED  (SDD emphasis, restored)",
            "collapse metrics (G-3, all four)",
            "scalar reward",
            "control arm: a policy that breaks near-ties at RANDOM  (SDD r2, "
            "restored) -- if it reproduces the same EE the dispersion was "
            "noise; if it cannot, there is a weak learned ordering",
            "perturbation stability  (SDD r2, restored)",
            "cross-seed ranking consistency  (SDD r2, restored)",
        ],
        "episodes": 9000,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "ablation_dimension": "learning_rate",
        "note": (
            "the only probe that needs training, so it is heavy compute and "
            "belongs on the server, not in the local probe pass"
        ),
    },
    "P7": {
        "question": "does anything actually constrain the action set?",
        "measures": [
            "per-term mask attrition: slot occupied / cell exists / cell "
            "visible, reported separately",
            "power-feasibility outage rate, both warm-start arms",
            "in-segment gain excursion against the 3.010 dB budget, and the "
            "required power of the steps judged infeasible",
        ],
        "policy": "random-masked, which stresses the mask hardest",
        "episodes": 100,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "ablation_dimension": "segment_warm_start",
        "note": (
            "⚠ NEW NUMBER 2026-08-23.  This was P5 and had displaced SDD's "
            "own P5; the number is vacated and the probe keeps its content. "
            "W-17 measured all three geometric terms and the power gate as "
            "non-binding at one hand-picked epoch, and W-19/W-22 then found "
            "the power gate DOES fire once segments are warm-started "
            "(0.94% main arm, 0.81% sensitivity arm).  P7 turns both into "
            "numbers over the frozen sampling distribution."
        ),
        "prototypes": [
            "scripts/outage_frozen.py",
            "scripts/ceiling_and_segments.py",
            "scripts/sensitivity_arm.py",
        ],
    },
}

PROBE_RNG_POLICY: str = (
    "Every probe with an ablation_dimension draws its sampling randomness "
    "from streams that are INDEPENDENT of the swept quantity: env_rng "
    "(fading), mobility_rng (users), a spawned stream for the warm-start "
    "ages, and the policy's own generator.  Measured with one shared "
    "generator on 2026-08-23, switching fading off also re-drew every later "
    "episode's segment ages and moved the outage count by 11 -- so the "
    "'fading ablation' had measured fading plus a different set of ages.  "
    "One generator produces numbers that look reasonable and are attributed "
    "wrongly, which is the hardest kind of error to see."
)
"""§7.1 methodology note (ruling W-23 §1), not a parameter.

It is frozen with the grid because P2, P4, P6 and P7 are all ablation-shaped
and would each carry the same defect if they shared a stream with the thing
they sweep.
"""

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

THRESHOLDS: dict[str, Any] = {
    "outage_dropped_transition_rate": {
        "value": OUTAGE_RATE_NEGLIGIBLE_DEFAULT,
        "class": "S",
        "meaning": (
            "above this, PATCH P-03's plain drop is inadmissible and the "
            "semi-MDP transition becomes mandatory (§4A.5a(4))"
        ),
        "rationale": (
            "1e-3 is one outage per hundred episodes at 100 users x 10 "
            "steps, too rare for a policy to find and exploit inside 9000 "
            "episodes.  It must be frozen BEFORE P1 because choosing it "
            "after seeing the rate is the leak §7.1 names."
        ),
    },
    "tle_malformed_record_fraction": {
        "value": MAX_MALFORMED_RECORD_FRACTION,
        "class": "S",
        "meaning": "quarantine ceiling; above it the corpus is rejected",
        "rationale": (
            "measured: exactly one malformed record in 3,545,756 (a BSTAR "
            "field overflowing its fixed width), i.e. 2.8e-7 — so 1e-3 "
            "leaves three orders of headroom over the observed rate while "
            "still failing loudly on a corrupt file"
        ),
    },
    "minimum_altitude_km": {
        "value": 300.0,
        "class": "S",
        "meaning": "D2 floor; below it a satellite is decaying, not serving",
        "rationale": (
            "the corpus contains healthy satellites at 156 km, so a naive "
            "'> 200 km' screen would have admitted them; 300 km is above "
            "the observed decay band and below every operational shell"
        ),
    },
    "coverage_target_fraction": {
        "value": 0.95,
        "class": "D",
        "meaning": "what V = 39 was sized to achieve",
        "measured": 0.9517,
    },
}

# ---------------------------------------------------------------------------
# Stopping rules
# ---------------------------------------------------------------------------

STOPPING_RULES: dict[str, Any] = {
    "training": {
        "episodes": 9000,
        "rule": "fixed episode count, no early stopping",
        "rationale": (
            "Table I fixes the budget.  Early stopping on a validation "
            "metric would make the stopping point a function of the data, "
            "which is the same leak as an adaptive threshold."
        ),
    },
    "checkpoint_selection": {
        "primary": "final-episode-policy",
        "secondary": "best-weighted-reward-on-eval",
        "assumption_id": "ASSUME-MODQN-REP-015",
        "rationale": (
            "the primary report is the final policy, so no selection over "
            "eval output enters the headline; the best-eval checkpoint is "
            "reported beside it and labelled as selected."
        ),
    },
    "probe": {
        "rule": "run the pre-registered episode count; no peeking, no extension",
        "rationale": (
            "extending a probe until a rate crosses a threshold is the "
            "adaptive-sampling leak in its purest form."
        ),
    },
    "abort": {
        "rule": (
            "a run aborts on any MCRLContractError and the abort is "
            "reported; it is never retried with a relaxed guard"
        ),
        "rationale": "P-3/G-11: a violated contract is a result, not a nuisance",
    },
}

# ---------------------------------------------------------------------------
# The two selection mappings (§7.1's "決定性的選取映射")
# ---------------------------------------------------------------------------

SELECTION_MAPPINGS: dict[str, Any] = {
    "Q-E dwell N": {
        "probe": "scenario characterisation, not a probe",
        "candidates": list(DWELL_N_CANDIDATES),
        "rule": (
            "take the LARGEST N in {2, 3, 4} whose measured re-key rate -- "
            "the fraction of dwell boundaries at which j = 0 moves -- is at "
            "or below 5%; if none qualifies, take the smallest"
        ),
        "rationale": (
            "independent of EE, throughput and every reported metric.  "
            "SDD 4A.2 gives dwell exactly one job: freeze j -> cell_id "
            "between boundaries so an action index keeps naming the same "
            "cell, which larger N serves better.  Its only cost is "
            "staleness -- the frozen map being wrong when the anchor should "
            "have moved -- and the re-key rate measures exactly that.  So "
            "the rule is 'as stable as possible, subject to not being "
            "stale': a correctness bound on the mechanism's own validity, "
            "not a performance target.  Monotone in N, so it cannot tie.  "
            "The earlier proposal (maximise the angle-aware EE dynamic "
            "range) was withdrawn: it selected on the effect the paper sets "
            "out to demonstrate."
        ),
        "resolved": 3,
        "measured_rekey_rate_at_decision_step": {
            "N=2": 0.02708,
            "N=3": 0.03819,
            "N=4": 0.05417,
        },
        "note": (
            "the rate depends only on the product N*dt -- a user travels at "
            "most 14.3% of a cell radius within a segment at any (N, dt) "
            "swept -- so this is a live decision only at dt >= 30 s.  At the "
            "former 1 s clock every candidate sat below 0.1% and the rule "
            "would have returned N = 4 by default."
        ),
        "unfreezes": "env.dwell.DWELL_N_IS_FROZEN",
    },
    "Q-F c1 calibration scale": {
        "probe": "P3 (already measured; no new run)",
        "rule": (
            "c_1 = the p95 of r1 over served steps, from P3's r1 quantiles"
        ),
        "rationale": (
            "The three scales cannot share one statistic, and the reason is "
            "structural rather than stylistic: r2 is bounded by a frozen "
            "parameter, r3 by the population, and r1 by nothing at all.  "
            "The common INTENT is that each normalised objective spans "
            "roughly unit range, so that omega_j means what Table I says it "
            "means -- the effective trade-off is omega_j / c_j, so c_1 "
            "directly sets how much of the headline result the first "
            "objective accounts for.  r1 = R_u/P^N is strictly positive and "
            "unbounded above, with a right tail driven by the best link "
            "geometry, so it has no analytic bound to normalise against; "
            "p95 spans the range while staying robust to that tail, which "
            "the max would track instead.  Same reasoning, same statistic, "
            "as the already-frozen c_3."
        ),
        "unfreezes": "trainer_spec.TrainerConfig.reward_calibration_scales[0]",
        "resolved": 2471140.576,
        "measured_r1_over_served_steps": {
            "p05": 60948.985, "p50": 508681.149, "p95": 2471140.576,
            "max": 6204625.88, "count": 12000.0,
            "source": "probe P3, 12000 decision steps",
        },
        "not_rounded_because": (
            "r3 is a head count and rounding keeps its scale countable; r1 "
            "is a continuous bit/J ratio with no unit to round to"
        ),
        "supersedes": {
            "legacy_c1": 117217362.202,
            "why": (
                "measured r1 has p50 = 5.09e5, so the legacy value is 230x "
                "too large; dividing by it would put r1's median at 0.0043 "
                "against |r3|'s 0.500 and crush the first objective.  "
                "'Invalid by construction' is now a measurement, not an "
                "inference."
            ),
        },
        "disclosure": (
            "⚠ P3 had already run when this rule was written, so r1's "
            "distribution was VISIBLE -- 'the rule preceded the numbers' is "
            "not literally true here the way it is for c_3.  What protects "
            "it: the rule is structural (unbounded -> p95; bounded -> the "
            "bound), it is the SAME rule already frozen for c_3, and it was "
            "not selected from among alternatives by looking at which "
            "produced a preferred balance.  Stated rather than glossed."
        ),
    },
    "Q-G c2 calibration scale": {
        "probe": "none -- closed analytically, no measurement needed",
        "rule": "c_2 = phi2, the larger handover penalty",
        "rationale": (
            "r2 is the one objective **bounded by construction**: (3.27) "
            "gives r2 in {0, -phi1, -phi2}, so |r2| <= phi2 always and "
            "dividing by phi2 normalises it to [0, 1] exactly.  Its scale is "
            "a frozen parameter, not a statistic, and closing it needs no "
            "probe at all -- it was determined the moment phi1 and phi2 "
            "were frozen.  ⚠ And the p95 rule CANNOT be transplanted here: "
            "r2's signed p95 is 0 because most steps have no handover, so "
            "'divide by the p95' would divide by zero.  The sign convention "
            "puts r2's informative end at p05, and p05 is exactly -phi2 by "
            "construction -- which is why the analytic bound is both simpler "
            "and exact."
        ),
        "unfreezes": "trainer_spec.TrainerConfig.reward_calibration_scales[1]",
        "resolved": 1.0,
        "measured_r2_over_all_steps": {
            "p05": -1.0, "p50": -0.0, "p95": 0.0, "mean": -0.11175,
            "note": "reported for the record; the rule uses none of it",
        },
    },
    "Q-D r3 calibration scale": {
        "probe": "P3",
        "rule": (
            "scale = the p95 of |r3| = U_{b_u} measured over P3's served "
            "steps, rounded to the nearest integer; r3 enters training as "
            "-U_{b_u} / scale"
        ),
        "rationale": (
            "B13 changed r3's units from a normalised gap to a raw user "
            "count, so the inherited scale means nothing for it.  p95 rather "
            "than max because the max is a single congested beam and would "
            "make the scale a function of one outlier; rounding to an "
            "integer keeps the divisor a countable quantity rather than a "
            "fitted one."
        ),
        "unfreezes": "env.service.R3_SCALE_IS_FROZEN",
        "resolved": 6,
        "measured_abs_r3_over_served_steps": {
            "p05": 1.0, "p50": 3.0, "p95": 6.0, "max": 8.0,
            "count": 11898.0, "source": "probe P3, 12000 decision steps",
        },
        "note": (
            "CLOSED by probe P3 on 2026-08-23 -- the first question here "
            "closed by a probe rather than a ruling.  The scale is applied "
            "through TrainerConfig.reward_calibration_*, which is why that "
            "surface survived P-05.  Measured under the reference policy at "
            "the frozen scenario; a trained policy spreads load differently "
            "but the scale stays frozen, because re-deriving it from "
            "training output would make the reward scale a function of the "
            "run it is scoring."
        ),
    },
}

SEGMENT_WARM_START: dict[str, Any] = {
    "main_arm": {
        "mode": "uniform-episode-length",
        "rule": "segment age a ~ Uniform{0, ..., H-1} at episode reset",
        "rationale": (
            "without it p(0) = p0 for 100% of users in every episode, which "
            "is an artefact of the episode boundary rather than a property "
            "of the geometry -- the same defect W-04 fixed for the D2 "
            "latches by priming them before step 0.  Parameter-free: it "
            "reuses H, so step 0 looks like a uniformly random step of an "
            "ongoing episode.  a = 0 keeps positive probability, so a "
            "genuinely fresh segment still occurs."
        ),
    },
    "sensitivity_arm": {
        "mode": "uniform-segment-length",
        "segment_age_steps": 6,
        "rule": "a ~ Uniform{0, ..., L-1} with L the UNCENSORED segment length",
        "L_provenance": (
            "6 steps: the median length of segments that end NATURALLY (by "
            "handover or outage) at dt = 30.08 s, measured under the "
            "reference policy at freeze time.  NOT the 5 of the pooled "
            "median -- 49.0% of segments are cut by the episode boundary "
            "and ran only 4.24 steps, so the pooled figure estimates a "
            "truncated quantity rather than the inter-renewal time this "
            "parameter is defined as."
        ),
        "rationale": (
            "For a deterministic segment length L the equilibrium age of an "
            "in-progress segment is Uniform{0, ..., L-1}, so this arm is not "
            "an alternative -- it IS the equilibrium distribution, with mean "
            "age 2.5 steps.  The two arms therefore carry complementary "
            "defects rather than one being better: the main arm is "
            "policy-independent by construction but draws ages 1.8x older "
            "than equilibrium (4.5 vs 2.5), which pushes p away from p0 and "
            "makes the mechanism look MORE active; this arm is the correct "
            "distribution but its L is measured UNDER THE REFERENCE POLICY, "
            "which is how a policy re-enters the initial state distribution. "
            "The main arm stays the headline because it is the "
            "pre-registered main arm -- switching after seeing a result is "
            "the thing pre-registration exists to prevent."
        ),
        "caveat": (
            "a trained policy will not hold links for the same length, so L "
            "is frozen as a reference-policy measurement and must be "
            "reported as one"
        ),
    },
    "user_position_in_the_back_projection": (
        "held at its current value; users travel 250 m per decision step, "
        "subtending 0.0297 deg at 483 km against a median per-step |dtheta| "
        "of 1.194 deg -- 2.5%, the same ratio that justifies leaving "
        "mobility on the decision clock"
    ),
}

# ---------------------------------------------------------------------------
# Reference policy and hold-out
# ---------------------------------------------------------------------------

REFERENCE_POLICY_SEED: int = 20260822
"""**S** — arbitrary but frozen; the date, so it is obviously not fitted."""

HOLDOUT_SEED: int = 8_140_291
"""**S** — the seed for the held-out evaluation draw, committed by hash.

Its value is sealed in the record as a salted digest rather than in the
clear, so the commitment can be verified afterwards without the number
having been available to anyone tuning against it (§7.1).
"""

HOLDOUT_SALT: str = "mcrl-leo-handover-2026-08-22"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_draft(
    *,
    ephemeris: EphemerisConfig | None = None,
    reference_policy_name: str = "stay-if-possible",
) -> dict[str, Any]:
    """Assemble the complete freeze-ready section set.

    Derivable values come from :func:`build_prereg_sections`, which reads
    them out of the modules that own them; only the pre-registration-only
    pieces above are supplied here.
    """
    config = ephemeris or EphemerisConfig()
    archive = config.archive()
    split = BlockAlternatingSplit.for_archive(archive)
    manifest = build_freeze_manifest(config, split)
    manifest = dict(manifest)
    manifest["sampling"] = EpisodeStartSampler.for_archive(
        archive, split, TRAIN
    ).as_dict()

    return build_prereg_sections(
        reference_policy=ReferencePolicy(
            name=reference_policy_name,
            seed=REFERENCE_POLICY_SEED,
            description="hold the previous association while it stays valid",
        ),
        probe_grid=PROBE_GRID | {"rng_policy": PROBE_RNG_POLICY},
        thresholds=THRESHOLDS,
        stopping_rules=STOPPING_RULES,
        ephemeris_manifest=manifest,
    ) | {
        "selection_mappings": SELECTION_MAPPINGS,
        "segment_warm_start": SEGMENT_WARM_START,
    }


def freeze(sections: dict[str, Any] | None = None) -> PreregRecord:
    """Seal the draft.  **Irreversible in the way that matters.**

    After this the probes may run, and any later change to a threshold or a
    selection mapping is a change made with knowledge of the data — which is
    what §7.1 exists to prevent.  Call it once, deliberately.
    """
    return freeze_prereg(
        sections if sections is not None else build_draft(),
        holdout_seed=HOLDOUT_SEED,
        salt=HOLDOUT_SALT,
    )
