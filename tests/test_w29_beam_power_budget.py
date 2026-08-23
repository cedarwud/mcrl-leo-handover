"""`V · p_max` against HOBS Table I's per-satellite budget (ruling B4).

`p_max = 1.65 W` had no stated source.  Three per-satellite power figures
were in circulation -- B4's `P_max = 100 W`, ch5's legacy `19.953 W`, and the
active contract's *no limit* (C-2) -- and `19.953 / 1.65 = 12.09` says the
1.65 most likely came from a **twelve**-beam satellite's budget.  That
premise died at `V = 39`.

The ruling declined to move the number (nothing showed it wrong, and moving
it would recompute `p0`, `p_sat` and all of ch5 §5.1) and declined B4's cap
form (C-2 keeps the model free of per-satellite limits, and a cap here would
re-add a gate outside the recurrence).  What it did instead was give 1.65 a
figure to be checked against.

A sentence in a paper cannot notice when `V` or `p_max` moves out from under
it.  This can.
"""

from __future__ import annotations

import pytest

from mcrl.env.cells import POINTING_CELL_COUNT
from mcrl.env.link_budget import (
    BEAM_POWER_MAX_W,
    HOBS_LEO_MAX_TRANSMIT_POWER_W,
    PA_SATURATION_POWER_W,
    SEGMENT_START_POWER_W,
)


def test_a_fully_loaded_satellite_stays_inside_the_hobs_budget():
    """`V · p_max <= P_max`.  The whole point of the ruling, in one line."""
    radiated_w = POINTING_CELL_COUNT * BEAM_POWER_MAX_W

    assert radiated_w == pytest.approx(64.35)
    assert radiated_w <= HOBS_LEO_MAX_TRANSMIT_POWER_W, (
        f"V = {POINTING_CELL_COUNT} beams at p_max = {BEAM_POWER_MAX_W} W "
        f"radiate {radiated_w:.2f} W, above HOBS Table I's "
        f"P_max = {HOBS_LEO_MAX_TRANSMIT_POWER_W} W. Either V or p_max has "
        "moved and ch5's budget-compatibility sentence is now false."
    )


def test_the_check_is_not_vacuous_at_the_scale_it_guards():
    """It has to be capable of failing, or it guards nothing.

    W-27 §5: a test that only passes because the system happens to sit in a
    comfortable state is testing the environment.  So push it -- at the
    twelve-beam premise the number came from there is enormous headroom, and
    at a plausible larger constellation it fails.
    """
    assert 12 * BEAM_POWER_MAX_W <= HOBS_LEO_MAX_TRANSMIT_POWER_W / 4.0
    assert 64 * BEAM_POWER_MAX_W > HOBS_LEO_MAX_TRANSMIT_POWER_W

    # And the margin at the frozen V is real but not large: about 36%.
    headroom = 1.0 - (POINTING_CELL_COUNT * BEAM_POWER_MAX_W) / (
        HOBS_LEO_MAX_TRANSMIT_POWER_W
    )
    assert 0.30 < headroom < 0.40


def test_the_reference_figure_is_not_wired_into_the_live_path():
    """C-2: this is a compatibility check, never a cap.

    If `HOBS_LEO_MAX_TRANSMIT_POWER_W` ever reaches the step loop it stops
    being a citation and becomes the per-satellite limit the contract
    excludes -- so assert nothing else imports it.
    """
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "mcrl"
    users = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*.py")
        if "HOBS_LEO_MAX_TRANSMIT_POWER_W" in path.read_text(encoding="utf-8")
    ]
    assert users == ["env/link_budget.py"], (
        f"the HOBS reference figure is now read by {users}; C-2 excludes a "
        "per-satellite power limit from the model, and a figure that is "
        "consulted at runtime is a limit however it is named"
    )


def test_p_max_still_pins_the_two_values_derived_from_it():
    """B4 kept 1.65 precisely so these would not move.  Say so mechanically."""
    assert PA_SATURATION_POWER_W == pytest.approx(5.2177, abs=1e-4)
    assert SEGMENT_START_POWER_W == pytest.approx(0.825)
