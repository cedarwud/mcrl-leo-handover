"""W-18 — the §7.1 draft must be complete and freezable, and stay unfrozen.

The draft is checked for the property that matters before sign-off: that it
would seal cleanly, so the freeze itself is one deliberate call rather than
a debugging session with the probes waiting.

Nothing here writes a frozen record.  A PREREG committed by a test run is a
PREREG nobody signed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcrl.env.constants import TLE_ROOT_DEFAULT
from mcrl.env.dwell import DWELL_N_CANDIDATES
from mcrl.runtime.prereg import (
    REQUIRED_SECTIONS,
    PreregFreezeError,
    assert_selection_mappings_cover_open_questions,
    open_questions,
)
from mcrl.runtime.prereg_draft import (
    PROBE_GRID,
    SELECTION_MAPPINGS,
    STOPPING_RULES,
    THRESHOLDS,
    build_draft,
    freeze,
)

requires_archive = pytest.mark.skipif(
    not Path(TLE_ROOT_DEFAULT).expanduser().is_dir(),
    reason="TLE archive not present",
)


@requires_archive
def test_the_draft_covers_every_required_section_and_none_are_empty():
    draft = build_draft()
    assert not [name for name in REQUIRED_SECTIONS if name not in draft]
    assert not [name for name in REQUIRED_SECTIONS if not draft[name]]


@requires_archive
def test_the_draft_would_freeze_cleanly():
    """Checked, not performed: the record is built and discarded."""
    record = freeze(build_draft())
    record.verify()
    assert record.digest
    # The hold-out seed is committed by digest, never in the clear.
    payload = record.as_dict()
    assert "8140291" not in str(payload)
    assert record.holdout.digest


def test_every_still_open_question_has_a_frozen_selection_mapping():
    """§7.1 accepts a rule instead of an answer — but not neither.

    Q-E closed on 2026-08-23 without running P2: its frozen rule needed
    only the re-key rate, which is scenario characterisation available
    before any policy is evaluated.  Its mapping stays in the record —
    a closed question still has to show the rule that closed it.
    """
    unresolved = {name for name, done in open_questions().items() if not done}
    assert unresolved == {"Q-D r3 calibration scale"}
    assert unresolved <= set(SELECTION_MAPPINGS)
    assert_selection_mappings_cover_open_questions(SELECTION_MAPPINGS)


def test_the_closed_question_records_what_closed_it():
    mapping = SELECTION_MAPPINGS["Q-E dwell N"]
    assert mapping["resolved"] == 3
    rates = mapping["measured_rekey_rate_at_decision_step"]
    assert rates["N=3"] <= 0.05 < rates["N=4"], "the rule must select 3 here"
    assert "withdrawn" in mapping["rationale"], (
        "the superseded EE-dynamic-range criterion must stay on the record"
    )


def test_a_selection_mapping_is_a_rule_not_an_answer():
    """A mapping that just named a value would be a decision, not a rule."""
    for name, mapping in SELECTION_MAPPINGS.items():
        assert "rule" in mapping and mapping["rule"], name
        assert "rationale" in mapping and mapping["rationale"], name
        assert "probe" in mapping, name
        # An OPEN question's mapping must not have quietly picked a value.
        if name in {n for n, done in open_questions().items() if not done}:
            assert "resolved" not in mapping, name
    assert SELECTION_MAPPINGS["Q-E dwell N"]["candidates"] == list(
        DWELL_N_CANDIDATES
    )


def test_dropping_a_selection_mapping_blocks_the_freeze():
    """The gate has teeth: it is what stops a placeholder being frozen."""
    with pytest.raises(PreregFreezeError, match="still open"):
        assert_selection_mappings_cover_open_questions(
            {"Q-E dwell N": SELECTION_MAPPINGS["Q-E dwell N"]}
        )


def test_every_probe_names_what_it_measures_and_what_it_closes():
    for name, probe in PROBE_GRID.items():
        assert probe["question"], name
        assert probe.get("measures") or probe.get("sweep"), name
        assert "closes" in probe, name
        assert "split_part" in probe, name
    closed = {q for probe in PROBE_GRID.values() for q in probe["closes"]}
    assert "Q-D" in closed, "every OPEN question needs an owning probe"
    # Q-E is closed already, so no probe may claim to close it -- running one
    # whose conclusion is settled would dress a decided number as a result.
    assert "Q-E" not in closed
    assert PROBE_GRID["P2"]["closes"] == []


def test_every_threshold_carries_its_class_and_its_reason():
    """An S-level number without a stated reason is a number somebody liked."""
    for name, entry in THRESHOLDS.items():
        assert "value" in entry, name
        if "class" in entry:
            assert entry["class"] in {"P", "P'", "D", "S", "X"}, name
        assert entry.get("rationale") or entry.get("measured"), name


def test_the_stopping_rules_forbid_data_dependent_stopping():
    assert STOPPING_RULES["training"]["episodes"] == 9000
    assert "no early stopping" in STOPPING_RULES["training"]["rule"]
    assert "no peeking" in STOPPING_RULES["probe"]["rule"]
    assert "never retried" in STOPPING_RULES["abort"]["rule"]


def test_the_sensitivity_arm_freezes_the_uncensored_segment_length():
    """``L = 6``, not the pooled median of 5 (ruling 2026-08-23).

    49.0% of segments are cut by the episode boundary and ran only 4.24
    steps, so the pooled median estimates a truncated quantity rather than
    the inter-renewal time this parameter is defined as.  At ``L = 6`` the
    arm is not an alternative to the main one — ``Uniform{0..L-1}`` **is**
    the equilibrium age distribution for a deterministic length ``L``, mean
    2.5 steps against the main arm's 4.5.
    """
    from mcrl.runtime.prereg_draft import SEGMENT_WARM_START

    arm = SEGMENT_WARM_START["sensitivity_arm"]
    assert arm["segment_age_steps"] == 6
    assert (arm["segment_age_steps"] - 1) / 2 == 2.5
    # It must say where L came from, and that it is policy-dependent.
    assert "reference policy" in arm["L_provenance"]
    assert "caveat" in arm and "trained policy" in arm["caveat"]


def test_both_warm_start_arms_are_constructible():
    """A frozen arm that cannot be instantiated is a frozen typo."""
    from mcrl.env.step import PhysicsConfig
    from mcrl.runtime.prereg_draft import SEGMENT_WARM_START

    for key in ("main_arm", "sensitivity_arm"):
        arm = SEGMENT_WARM_START[key]
        PhysicsConfig(
            segment_warm_start=arm["mode"],
            segment_age_steps=arm.get("segment_age_steps", 0),
        )


# ---------------------------------------------------------------------------
# The drift guard (W-24): a probe number carries an obligation
# ---------------------------------------------------------------------------
#
# On 2026-08-23 the controller found that P5 had been taken over by a
# different probe, so SDD §4's own P5 -- the receive-angle disclosure for
# (3.10c) -- had no owner.  Cross-checking the rest the same way turned up
# three more numbers that had quietly narrowed.  These tests encode the two
# rules that would have caught all four.

SDD_OBLIGATIONS: dict[str, tuple[str, ...]] = {
    "P1": ("visible", "handover", "elevation"),
    "P2": ("P^N swing", "dynamic range"),
    "P3": ("width of U_{b_u}", "argmax agreement"),
    "P5": ("theta^R_min", "below theta^R_min"),
    "P6": ("q_margin, NORMALISED", "at RANDOM", "erturbation", "cross-seed"),
}
"""Fragments SDD §4 names as each probe's REQUIRED output.

Deliberately keyed by number, not by question: the failure mode was a
number keeping its slot while its content changed underneath.
"""


@pytest.mark.parametrize("number,fragments", sorted(SDD_OBLIGATIONS.items()))
def test_each_probe_still_carries_what_the_sdd_asks_it_for(number, fragments):
    probe = PROBE_GRID[number]
    text = " ".join(probe.get("measures", [])) + " " + str(
        probe.get("sdd_definition", "")
    )
    for fragment in fragments:
        assert fragment in text, (
            f"{number} no longer reports {fragment!r}; SDD §4 lists it as a "
            "required output.  Restore it or get the SDD changed -- do not "
            "let the number keep the slot while the obligation disappears."
        )


def test_a_reused_probe_number_says_what_it_displaced():
    """P4 and P7 both took a number; each must say so on the record."""
    assert "vacant" in PROBE_GRID["P4"]["note"]
    assert "UNRELATED" in PROBE_GRID["P4"]["note"]
    assert "NEW NUMBER" in PROBE_GRID["P7"]["note"]
    assert "P5" in PROBE_GRID["P7"]["note"], (
        "P7 must record that it vacated P5, or the next reader will not know "
        "why the numbering skips"
    )
    assert "RESTORED" in PROBE_GRID["P5"]["note"]


def test_every_ablation_shaped_probe_is_covered_by_the_rng_policy():
    """W-23 §1: one generator makes an ablation measure the wrong thing."""
    from mcrl.runtime.prereg_draft import PROBE_RNG_POLICY

    swept = [
        name
        for name, probe in PROBE_GRID.items()
        if probe.get("ablation_dimension")
    ]
    assert set(swept) == {"P2", "P4", "P6", "P7"}, swept
    assert "INDEPENDENT" in PROBE_RNG_POLICY
    assert "attributed" in PROBE_RNG_POLICY


def test_the_probe_grid_is_frozen_with_the_rng_policy():
    from mcrl.runtime.prereg_draft import build_draft

    draft = build_draft()
    assert draft["probe_grid"]["P7"]["question"]
    assert "rng_policy" in draft["probe_grid"], (
        "the methodology note must travel with the grid, not beside it"
    )
