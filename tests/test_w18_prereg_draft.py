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


def test_both_open_questions_have_a_frozen_selection_mapping():
    """§7.1 accepts a rule instead of an answer — but not neither."""
    unresolved = [name for name, done in open_questions().items() if not done]
    assert set(unresolved) == set(SELECTION_MAPPINGS)
    assert_selection_mappings_cover_open_questions(SELECTION_MAPPINGS)


def test_a_selection_mapping_is_a_rule_not_an_answer():
    """A mapping that just named a value would be a decision, not a rule."""
    for name, mapping in SELECTION_MAPPINGS.items():
        assert "rule" in mapping and mapping["rule"], name
        assert "rationale" in mapping and mapping["rationale"], name
        assert "probe" in mapping, name
        # The dwell rule must not have quietly picked one already.
        assert not any(
            isinstance(value, (int, float)) and not isinstance(value, bool)
            for key, value in mapping.items()
            if key not in {"candidates"}
        ), name
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
    assert {"Q-D", "Q-E"} <= closed, "the open questions need an owning probe"


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
