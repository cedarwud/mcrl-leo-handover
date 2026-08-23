"""G-6 — SDD §8's forbidden list must not reach the live training path.

Gate G-6: "§8 全部項目 grep 為零命中(於 live 訓練路徑)".

The grep is scoped, not blanket.  SDD §8 says the code is *kept* for later
ablation and merely must not be **wired up**, so the gate has to distinguish
"present in a byte-for-byte ported file, inert" from "reachable from
training".  This test does that by naming the two ported files that still
carry the vocabulary and requiring every other module to be clean — so the
count can only shrink, and W-09 has an explicit target.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mcrl.runtime.trainer_spec import TrainerConfig

SRC = Path(__file__).resolve().parents[1] / "src" / "mcrl"

FORBIDDEN_TERMS = (
    "v_max",
    "k_cap",
    "capacity_penalty",
    "auction",
    "catfish",
    "double_dqn",
    "z_score",
    "zscore",
)

AWAITING_W09: dict[str, set[str]] = {}
"""**Empty since W-09.**  It must stay empty.

It used to exempt ``runtime/trainer_spec.py`` (the whole Phase-04B..07D
config surface) and one ``env/step_types.py`` docstring.  W-09 removed
both, so the §8 vocabulary now appears nowhere in ``src/`` at all — not
even in prose explaining why a mechanism is absent, because a
"comments do not count" carve-out would hollow the gate out.

Re-adding an entry means something reachable acquired the vocabulary.
Delete the code, not the assertion.
"""

# NOTE (2026-08-22): the execution mask ``m^e`` was REMOVED from §8.  B10
# predated B13; once ``r3`` became ``-U_{b_u}`` its correctness came to
# depend on who is actually served, which is exactly what ``m^e`` gates, and
# §3.7 P-5 lists it as mandatory.  Dropping the contribution claim did not
# require dropping the behaviour.  It must NOT be re-added to the list above.


def _python_files() -> list[Path]:
    return sorted(path for path in SRC.rglob("*.py"))


def test_no_new_module_mentions_a_forbidden_term():
    offenders: list[str] = []
    for path in _python_files():
        relative = path.relative_to(SRC).as_posix()
        allowed = AWAITING_W09.get(relative, set())
        text = path.read_text().lower()
        for term in FORBIDDEN_TERMS:
            if term in text and term not in allowed:
                offenders.append(f"{relative}: {term}")
    assert not offenders, "forbidden vocabulary outside its exemption:\n" + "\n".join(
        offenders
    )


def test_the_exemption_map_is_empty():
    """W-09 emptied it; nothing may put it back."""
    assert AWAITING_W09 == {}


def test_the_exemptions_are_still_needed_and_no_wider_than_needed():
    """A stale exemption is as bad as a missing one — it hides a regression."""
    for relative, terms in AWAITING_W09.items():
        text = (SRC / relative).read_text().lower()
        for term in terms:
            assert term in text, (
                f"{relative} no longer contains {term!r}: drop the exemption"
            )


REMOVED_CONFIG_FIELDS = (
    "catfish_enabled",
    "catfish_ablation",
    "catfish_intervention_enabled",
    "catfish_competitive_shaping_enabled",
    "catfish_objective_admission_rule",
    "catfish_specialist_mode",
    "anti_collapse_action_constraint_enabled",
    "anti_collapse_constraint_mode",
    "anti_collapse_max_users_per_beam",
    "popart_enabled",
    "section_6_2_row_capture_enabled",
)


@pytest.mark.parametrize("field", REMOVED_CONFIG_FIELDS)
def test_the_opt_in_surfaces_are_gone_not_merely_disabled(field):
    """W-09: a disabled field is a socket; an absent one is not.

    A field defaulting to False still invites a reader to set it to True and
    expect something — and here nothing would have happened, because the code
    it switched was never ported.
    """
    assert not hasattr(TrainerConfig(), field)


def test_the_surviving_calibration_switch_is_now_live_and_carries_real_scales():
    """``reward_calibration_*`` survived P-05 for this; Q-D/Q-F/Q-G closed it.

    ⚠ It was asserted OFF by default until 2026-08-23.  Leaving it off is
    not the safe choice it looks like: uncalibrated, the ``ω₁r₁`` term is
    4.1e5 times ``ω₃r₃`` and 7.6e6 times ``ω₂r₂``, so the three-objective
    problem degenerates into single-objective ``r₁``.  "Disabled" would
    have frozen a degenerate training setup.
    """
    from mcrl.runtime.reward_calibration import REWARD_SCALES

    config = TrainerConfig()
    assert config.reward_calibration_enabled is True
    assert config.reward_calibration_mode == "divide-by-fixed-scales"
    assert config.reward_calibration_scales == REWARD_SCALES
    # And every scale is a real one, not a placeholder 1.0 triple.
    assert config.reward_calibration_scales != (1.0, 1.0, 1.0)


def test_the_new_environment_modules_are_entirely_clean():
    """Nothing written for this project may carry the vocabulary at all."""
    new_modules = [
        "env/action_contract.py",
        "env/antenna.py",
        "env/cells.py",
        "env/constants.py",
        "env/d2.py",
        "env/dwell.py",
        "env/ephemeris.py",
        "env/geometry.py",
        "env/interference.py",
        "env/link_budget.py",
        "env/pointing.py",
        "env/scenario.py",
        "env/service.py",
        "env/step.py",
        "env/tle.py",
        "runtime/bessel.py",
        "runtime/energy_efficiency.py",
        "runtime/finiteness.py",
        "runtime/outage_gate.py",
    ]
    for relative in new_modules:
        text = (SRC / relative).read_text().lower()
        for term in FORBIDDEN_TERMS:
            assert term not in text, f"{relative} mentions {term!r}"
