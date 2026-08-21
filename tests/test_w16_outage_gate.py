"""SDD §4A.5a(4) — the outage gate (author ruling 2026-08-22).

Dropping an outage transition is admissible only while outage is rare.  The
reason is not data loss: every reward component reads as neutral during an
outage, so truncating the future on top makes going dark **free** — the
same hole the re-entry ``φ2`` of §4A.4 exists to close.
"""

from __future__ import annotations

import numpy as np
import pytest

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.errors import MCRLContractError
from mcrl.runtime.outage_gate import (
    OUTAGE_RATE_NEGLIGIBLE_DEFAULT,
    assert_drop_is_admissible,
    evaluate_outage_gate,
)
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv

NUM_BEAMS = 8


def _diagnostics(steps: int, no_op: int = 0, all_invalid: int = 0):
    return {
        "decision_steps_seen": steps,
        "no_op_transitions_skipped": no_op,
        "all_invalid_next_transitions_skipped": all_invalid,
    }


def test_a_clean_run_is_admissible():
    verdict = evaluate_outage_gate(_diagnostics(100_000))
    assert verdict.dropped_rate == 0.0
    assert not verdict.semi_mdp_required
    assert verdict.verdict == "drop-admissible"


def test_a_rate_above_the_ceiling_makes_semi_mdp_mandatory():
    verdict = evaluate_outage_gate(_diagnostics(100_000, no_op=500))
    assert verdict.dropped_rate == pytest.approx(5e-3)
    assert verdict.semi_mdp_required
    assert verdict.verdict == "semi-mdp-required"


def test_both_drop_reasons_count_toward_the_rate():
    verdict = evaluate_outage_gate(
        _diagnostics(10_000, no_op=6, all_invalid=6)
    )
    assert verdict.total_dropped == 12
    assert verdict.dropped_rate == pytest.approx(1.2e-3)
    assert verdict.semi_mdp_required
    # The no-op rate alone would have passed; reporting only it would hide it.
    assert verdict.no_op_rate == pytest.approx(6e-4)


def test_the_assertion_names_the_obligation_not_a_bug():
    with pytest.raises(MCRLContractError, match="semi-MDP transition"):
        assert_drop_is_admissible(_diagnostics(10_000, no_op=100))


def test_the_assertion_passes_below_the_ceiling():
    verdict = assert_drop_is_admissible(_diagnostics(10_000, no_op=1))
    assert verdict.dropped_rate == pytest.approx(1e-4)


def test_the_threshold_is_explicit_and_overridable():
    assert OUTAGE_RATE_NEGLIGIBLE_DEFAULT == 1e-3
    diagnostics = _diagnostics(10_000, no_op=50)
    assert evaluate_outage_gate(diagnostics, threshold=1e-2).verdict == (
        "drop-admissible"
    )
    assert evaluate_outage_gate(diagnostics, threshold=1e-3).verdict == (
        "semi-mdp-required"
    )


def test_missing_diagnostics_fail_loud():
    with pytest.raises(MCRLContractError, match="missing"):
        evaluate_outage_gate({"no_op_transitions_skipped": 0})


def test_an_out_of_range_threshold_is_refused():
    with pytest.raises(ValueError):
        evaluate_outage_gate(_diagnostics(10), threshold=0.0)


def test_the_gate_reads_a_real_training_run():
    """End to end: the trainer's own counters feed the gate."""
    steps = 4
    script = np.ones((steps + 1, 2, NUM_BEAMS), dtype=bool)
    script[2, 0, :] = False  # user 0 goes dark at step 2
    env = ScriptedEnv(script, num_beams=NUM_BEAMS, steps_per_episode=steps)
    config = TrainerConfig(
        batch_size=10_000,
        episodes=1,
        epsilon_start=0.0,
        epsilon_end=0.0,
        epsilon_decay_episodes=1,
    )
    trainer = MODQNTrainer(env, config)
    trainer.train()

    verdict = evaluate_outage_gate(trainer.get_masking_diagnostics())
    assert verdict.decision_steps == steps * 2
    assert verdict.no_op_dropped == 1
    assert verdict.all_invalid_next_dropped == 1
    # One outage in eight decision steps is nowhere near negligible.
    assert verdict.semi_mdp_required


def test_resetting_the_counters_clears_the_denominator_too():
    steps = 2
    env = ScriptedEnv(
        np.ones((steps + 1, 2, NUM_BEAMS), dtype=bool),
        num_beams=NUM_BEAMS,
        steps_per_episode=steps,
    )
    trainer = MODQNTrainer(env, TrainerConfig(batch_size=10_000, episodes=1))
    trainer.train()
    assert trainer.get_masking_diagnostics()["decision_steps_seen"] > 0
    trainer.reset_masking_diagnostics()
    assert trainer.get_masking_diagnostics() == {
        "no_op_transitions_skipped": 0,
        "all_invalid_next_transitions_skipped": 0,
        "decision_steps_seen": 0,
    }
