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

PROBE_GRID: dict[str, Any] = {
    "P1": {
        "question": "Q-A/Q-B: visibility and D2 event rate under a fixed policy",
        "measures": [
            "D2-eligible satellites per user per step",
            "valid actions per user per step, and the starvation rate",
            "handover events split phi1 / phi2 / re-entry, from realised "
            "associations and never from indices",
            "elevation and its rate of change",
            "outage_infeasible rate — the §4A.5a(4) input",
        ],
        "policy": "all three reference policies, reported separately",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": ["Q-A", "Q-B"],
    },
    "P2": {
        "question": "Q-E: the dwell length N",
        "sweep": {"dwell_steps": list(DWELL_N_CANDIDATES)},
        "measures": [
            "angle-aware EE dynamic range across the swept N",
            "re-key rate and the fraction of re-keys that move j = 0",
            "handover rate attributable to re-keying rather than to geometry",
        ],
        "policy": "stay-if-possible",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": ["Q-E"],
    },
    "P3": {
        "question": "Q-D: the r3 recalibration scale, and objective separability",
        "measures": [
            "distribution of U_{b_u} across the population",
            "|r1|, |r2|, |r3| magnitudes on the same steps",
            "correlation between r1 and r3 across steps — they must be "
            "separable, which is what F-2's per-link power sum destroyed",
        ],
        "policy": "all three reference policies",
        "episodes": 200,
        "users": 100,
        "split_part": TRAIN,
        "closes": ["Q-D"],
    },
    "P4": {
        "question": "does the interference model bind? which term dominates?",
        "measures": [
            "I^intra / I^inter split per served link",
            "SINR distribution with and without the co-colour sum",
            "how often two satellites illuminate one cell — (3.12b)'s v' = v",
        ],
        "policy": "all three reference policies",
        "episodes": 100,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
    },
    "P5": {
        "question": "does anything actually constrain the action set?",
        "measures": [
            "per-term mask attrition: slot occupied / cell exists / cell "
            "visible, reported separately",
            "power-feasibility outage rate and the in-segment gain loss "
            "against the 3.010 dB budget",
        ],
        "policy": "random-masked, which stresses the mask hardest",
        "episodes": 100,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "note": (
            "W-17 measured all three geometric terms and the power gate as "
            "non-binding (28/28 actions valid, outage 0/12000).  P5 is what "
            "turns that observation into a reported number over the frozen "
            "sampling distribution rather than one hand-picked epoch."
        ),
    },
    "P6": {
        "question": "the learning-rate sweep (ruling C-13)",
        "sweep": {"learning_rate": [0.01, 0.003, 0.001]},
        "measures": ["q_margin", "collapse metrics (G-3, all four)", "scalar reward"],
        "episodes": 9000,
        "users": 100,
        "split_part": TRAIN,
        "closes": [],
        "note": "heavy compute; server-side, not part of the probe pass",
    },
}

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
        "probe": "P2",
        "candidates": list(DWELL_N_CANDIDATES),
        "rule": (
            "choose the N in {2, 3, 4} maximising the angle-aware EE dynamic "
            "range (p95 - p05 of the per-link EE over the probe); ties broken "
            "by the SMALLEST N"
        ),
        "rationale": (
            "the dwell length exists so the earth-fixed pointing is stable "
            "within a segment; what it must not do is flatten the angle "
            "signal the first objective is built on.  Dynamic range is that "
            "property directly.  The tie-break favours the smaller N because "
            "a shorter segment tracks the geometry more closely and the "
            "feasibility argument uses the >=10 deg service window of 6.3 "
            "min, not the horizon-to-horizon 10.5 min."
        ),
        "unfreezes": "env.dwell.DWELL_N_IS_FROZEN",
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
        "note": (
            "the scale is applied through TrainerConfig.reward_calibration_*, "
            "which is why that surface survived P-05."
        ),
    },
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
        probe_grid=PROBE_GRID,
        thresholds=THRESHOLDS,
        stopping_rules=STOPPING_RULES,
        ephemeris_manifest=manifest,
    ) | {"selection_mappings": SELECTION_MAPPINGS}


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
