"""W-13 — the PREREG freezer and the data-blindness guard (SDD §7.1, §4).

§7.1's whole point is that a threshold chosen after seeing the number it
bounds is a leak.  A document cannot enforce that; these are the mechanical
parts that can.
"""

from __future__ import annotations

import json

import pytest

from mcrl.errors import MCRLContractError
from mcrl.runtime.prereg import (
    PREREG_SCHEMA,
    REQUIRED_SECTIONS,
    DataBlindnessError,
    HoldoutCommitment,
    PreregFreezeError,
    PreregRecord,
    ReferencePolicy,
    assert_data_blind,
    assert_ready_to_train,
    assert_selection_mappings_cover_open_questions,
    build_prereg_sections,
    freeze_prereg,
    open_questions,
    read_prereg,
    write_prereg,
)

POLICY = ReferencePolicy(
    name="nearest-eligible",
    seed=20260822,
    description="serve the highest-margin eligible satellite, own cell",
)


SELECTION_MAPPINGS = {
    "Q-E dwell N": (
        "N is whichever of {2,3,4} maximises the angle-aware EE dynamic "
        "range in P2; ties broken by the smallest N"
    ),
    "Q-D r3 calibration scale": (
        "the r3 scale is the p95 of |U_{b_u}| over the P3 reference rollout, "
        "rounded up to the next integer"
    ),
}


def _sections(selection_mappings=None):
    sections = build_prereg_sections(
        reference_policy=POLICY,
        probe_grid={
            "P1": {"visibility": True, "d2_event_rate": True},
            "P2": {"dwell_n": [2, 3, 4]},
            "P3": {"r3_discriminability": True},
            "P5": {"rx_angle_distribution": True},
            "P6": {"learning_rate": [0.01, 0.003, 0.001]},
        },
        thresholds={"outage_rate_ceiling": 1e-3},
        stopping_rules={"max_retries": 0, "on_failure": "abort"},
        ephemeris_manifest={
            "file_set_sha256": "0" * 64,
            "split": {"scheme": "block-alternating-with-embargo"},
            "sampling": {"train": {"part": "train"}},
        },
    )
    sections["selection_mappings"] = (
        SELECTION_MAPPINGS if selection_mappings is None else selection_mappings
    )
    return sections


# -- open questions block the freeze --------------------------------------


def test_the_open_questions_are_read_from_the_code_that_owns_them():
    questions = open_questions()
    assert set(questions) == {"Q-E dwell N", "Q-D r3 calibration scale"}
    assert questions == {"Q-E dwell N": False, "Q-D r3 calibration scale": False}


def test_freezing_with_open_questions_is_the_normal_case():
    """The probes that close Q-D and Q-E must not run until this exists.

    Requiring their values first would be circular; §7.1 asks for a
    deterministic selection mapping instead.
    """
    record = freeze_prereg(_sections(), holdout_seed=1)
    assert record.schema == PREREG_SCHEMA
    assert record.sections["selection_mappings"]["Q-E dwell N"]


def test_an_open_question_without_a_selection_mapping_blocks_the_freeze():
    with pytest.raises(PreregFreezeError, match="Q-E dwell N"):
        assert_selection_mappings_cover_open_questions({})
    with pytest.raises(PreregFreezeError, match="no frozen selection"):
        freeze_prereg(_sections(selection_mappings={}), holdout_seed=1)


def test_a_partial_selection_mapping_still_blocks():
    partial = {"Q-E dwell N": SELECTION_MAPPINGS["Q-E dwell N"]}
    with pytest.raises(PreregFreezeError, match="Q-D r3 calibration scale"):
        freeze_prereg(_sections(selection_mappings=partial), holdout_seed=1)


def test_training_is_what_the_freeze_flags_actually_block():
    """Freezing with Q-D/Q-E open is fine; training against a placeholder is not."""
    freeze_prereg(_sections(), holdout_seed=1)
    with pytest.raises(PreregFreezeError, match="training run"):
        assert_ready_to_train()


# -- completeness ----------------------------------------------------------


def test_every_required_section_must_be_present():
    sections = _sections()
    del sections["thresholds"]
    with pytest.raises(PreregFreezeError, match="thresholds"):
        freeze_prereg(sections, holdout_seed=1)


def test_an_empty_section_is_not_a_frozen_section():
    sections = _sections()
    sections["probe_grid"] = {}
    with pytest.raises(PreregFreezeError, match="present but empty"):
        freeze_prereg(sections, holdout_seed=1)


def test_the_required_sections_cover_what_7_1_names():
    for name in (
        "probe_grid",
        "thresholds",
        "stopping_rules",
        "reference_policy",
        "selection_mappings",
    ):
        assert name in REQUIRED_SECTIONS


# -- the sections are derived, not transcribed ----------------------------


def test_the_parameters_are_read_out_of_the_code_that_implements_them():
    """A hand-copied PREREG drifts, and the document is the one people trust."""
    sections = _sections()
    assert sections["action_and_state"]["state_dim"] == 125
    assert sections["action_and_state"]["actions"] == 28
    assert sections["training"]["epsilon_decay_episodes"] == 2000
    assert sections["d2"]["thresh2_km"] == 1100.0
    assert sections["antenna_and_link_budget"]["bessel_series_max_abs_x"] == 34.0
    assert sections["dwell"]["candidates"] == [2, 3, 4]


def test_the_deleted_ceilings_are_recorded_as_absent_not_omitted():
    """Ruling 2026-08-22: their absence is a decision and must be visible."""
    budget = _sections()["antenna_and_link_budget"]
    assert "beam_count_ceiling" in budget
    assert budget["beam_count_ceiling"] is None
    assert budget["satellite_power_ceiling"] is None


def test_the_learning_rate_is_recorded_as_a_controlled_variable():
    """SDD §7: it must not take either side's default."""
    assert "CONTROLLED" in _sections()["training"]["learning_rate"]


def test_beam_activation_is_recorded_as_derived():
    assert _sections()["action_and_state"]["beam_activation"] == "z = 1{U > 0}, derived"


# -- the hold-out commitment ----------------------------------------------


def test_a_commitment_binds_without_revealing_the_seed():
    commitment = HoldoutCommitment.commit(4242)
    assert "4242" not in commitment.digest
    assert len(commitment.digest) == 64
    commitment.verify(4242)


def test_a_seed_chosen_later_cannot_satisfy_the_commitment():
    """§7.1's inaccessible hold-out generator, made checkable."""
    commitment = HoldoutCommitment.commit(4242)
    with pytest.raises(PreregFreezeError, match="chosen after seeing the data"):
        commitment.verify(9999)


def test_the_same_seed_under_a_different_salt_gives_a_different_digest():
    assert HoldoutCommitment.commit(1, salt="a").digest != HoldoutCommitment.commit(
        1, salt="b"
    ).digest


def test_the_commitment_round_trips_through_the_record(tmp_path):
    record = freeze_prereg(_sections(), holdout_seed=777)
    restored = read_prereg(write_prereg(tmp_path / "prereg.json", record))
    restored.holdout.verify(777)
    with pytest.raises(PreregFreezeError):
        restored.holdout.verify(778)


# -- the record hashes itself ---------------------------------------------


def test_a_frozen_record_detects_a_later_edit(tmp_path):
    record = freeze_prereg(_sections(), holdout_seed=1)
    path = write_prereg(tmp_path / "prereg.json", record)

    payload = json.loads(path.read_text())
    payload["sections"]["thresholds"]["outage_rate_ceiling"] = 0.5
    path.write_text(json.dumps(payload))

    with pytest.raises(PreregFreezeError, match="edited after freezing"):
        read_prereg(path)


def test_an_unhashed_record_is_not_a_frozen_one():
    record = PreregRecord(
        sections={"a": 1}, holdout=HoldoutCommitment.commit(1)
    )
    with pytest.raises(PreregFreezeError, match="never frozen"):
        record.verify()


def test_an_unknown_schema_is_refused():
    with pytest.raises(PreregFreezeError, match="schema"):
        PreregRecord.from_dict({"schema": "something-else", "sections": {}})


def test_a_clean_round_trip_verifies(tmp_path):
    record = freeze_prereg(_sections(), holdout_seed=5)
    restored = read_prereg(write_prereg(tmp_path / "p.json", record))
    assert restored.digest == record.digest
    assert restored.sections == record.sections


# -- data blindness --------------------------------------------------------


def test_a_declared_reference_policy_is_accepted():
    assert assert_data_blind(policy=POLICY) is POLICY


def test_an_untrained_network_is_not_data_blind():
    """SDD §4 r2, the correction that matters most here.

    r1 allowed an untrained network.  Three reviewers pointed out that its
    argmax follows from initialisation and feature scale, so the probe would
    be measuring the initialisation rather than the environment.
    """
    import torch.nn as nn

    with pytest.raises(DataBlindnessError, match="initialisation"):
        assert_data_blind(policy=nn.Linear(4, 4))


def test_a_trainer_is_not_a_reference_policy():
    import numpy as np

    from mcrl.algorithms.modqn import MODQNTrainer
    from mcrl.env.action_contract import NUM_ACTIONS
    from mcrl.runtime.trainer_spec import TrainerConfig

    from _fake_env import ScriptedEnv

    trainer = MODQNTrainer(
        ScriptedEnv(np.ones((2, 2, NUM_ACTIONS), dtype=bool), num_beams=NUM_ACTIONS),
        TrainerConfig(batch_size=4, episodes=1),
    )
    with pytest.raises(DataBlindnessError, match="ReferencePolicy"):
        assert_data_blind(policy=trainer)


@pytest.mark.parametrize(
    "artefact", ["final.pt", "best_eval.pth", "run/model.ckpt", "w.safetensors"]
)
def test_a_probe_may_not_read_a_training_checkpoint(artefact):
    with pytest.raises(DataBlindnessError, match="training checkpoint"):
        assert_data_blind(policy=POLICY, inputs=[artefact])


def test_ordinary_probe_inputs_are_allowed():
    assert_data_blind(
        policy=POLICY,
        inputs=["starlink_20260820.tle", "freeze.json", "survey.json"],
    )


def test_the_reference_policy_carries_its_seed_into_the_record():
    recorded = _sections()["reference_policy"]
    assert recorded["seed"] == POLICY.seed
    assert recorded["name"] == "nearest-eligible"


def test_a_nameless_reference_policy_is_refused():
    with pytest.raises(ValueError, match="needs a name"):
        ReferencePolicy(name="", seed=1)


def test_the_guard_errors_are_contract_errors():
    assert issubclass(DataBlindnessError, MCRLContractError)
    assert issubclass(PreregFreezeError, MCRLContractError)
