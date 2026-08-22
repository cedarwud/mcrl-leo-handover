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

AWAITING_W09 = {
    # Ported byte-for-byte; the vocabulary is inert config surface.
    "runtime/trainer_spec.py": {"catfish"},
    # A docstring mentioning the old registry name for v_max.
    "env/step_types.py": {"k_cap"},
}
"""Every exemption names the file **and** the terms it may still contain.

W-09 ("拆掉 v_max/penalty;χ 預設關閉") empties this map.
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


def test_the_exemptions_are_still_needed_and_no_wider_than_needed():
    """A stale exemption is as bad as a missing one — it hides a regression."""
    for relative, terms in AWAITING_W09.items():
        text = (SRC / relative).read_text().lower()
        for term in terms:
            assert term in text, (
                f"{relative} no longer contains {term!r}: drop the exemption"
            )


@pytest.mark.parametrize(
    "field, expected",
    [
        ("catfish_enabled", False),
        ("catfish_intervention_enabled", False),
        ("catfish_competitive_shaping_enabled", False),
        ("anti_collapse_action_constraint_enabled", False),
        ("popart_enabled", False),
        ("reward_calibration_enabled", False),
        ("section_6_2_row_capture_enabled", False),
    ],
)
def test_every_forbidden_surface_is_off_by_default(field, expected):
    """Inert is only inert while the default says so."""
    assert getattr(TrainerConfig(), field) is expected


def test_the_disabled_modes_are_the_declared_ones():
    config = TrainerConfig()
    assert config.anti_collapse_constraint_mode == "disabled"
    assert config.catfish_ablation == "none"
    assert config.catfish_objective_admission_rule == "disabled"
    assert config.catfish_specialist_mode == "disabled"


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
        "env/link_budget.py",
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
