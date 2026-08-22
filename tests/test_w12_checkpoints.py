"""W-12 — checkpoint payloads and their round trip.

The last module W-01 could not satisfy.  Ported trimmed: the source package
is 863 lines across five modules and carries run-metadata, log-row, and
compatibility types for artifact formats this project does not produce.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from mcrl.algorithms.modqn import MODQNTrainer
from mcrl.artifacts import (
    CheckpointPayloadV1,
    CheckpointRuleV1,
    read_checkpoint,
    write_checkpoint,
)
from mcrl.artifacts.models import CHECKPOINT_FORMAT_VERSION
from mcrl.env.action_contract import NUM_ACTIONS
from mcrl.errors import MCRLContractError
from mcrl.runtime.trainer_spec import TrainerConfig

from _fake_env import ScriptedEnv


def _trainer():
    env = ScriptedEnv(
        np.ones((3, 2, NUM_ACTIONS), dtype=bool),
        num_beams=NUM_ACTIONS,
        steps_per_episode=2,
    )
    return MODQNTrainer(env, TrainerConfig(batch_size=4, episodes=1))


def _rule():
    return CheckpointRuleV1(
        assumption_id="ASSUME-MODQN-REP-015",
        primary_report="final-episode-policy",
        secondary_report="best-weighted-reward-on-eval",
        secondary_implemented=False,
        secondary_status="no eval seed set",
    )


# -- round trip ------------------------------------------------------------


def test_a_payload_survives_a_write_and_read(tmp_path):
    trainer = _trainer()
    payload = trainer.build_checkpoint_payload(episode=7, checkpoint_kind="final")
    path = write_checkpoint(tmp_path / "run" / "final.pt", payload)
    assert path.is_file()

    restored = read_checkpoint(path)
    assert restored.episode == 7
    assert restored.checkpoint_kind == "final"
    assert restored.state_dim == trainer.state_dim
    assert restored.action_dim == trainer.action_dim
    assert restored.format_version == CHECKPOINT_FORMAT_VERSION


def test_the_weights_come_back_identical(tmp_path):
    trainer = _trainer()
    payload = trainer.build_checkpoint_payload(episode=1, checkpoint_kind="final")
    restored = read_checkpoint(write_checkpoint(tmp_path / "c.pt", payload))

    for objective in range(3):
        original = trainer.q_nets[objective].state_dict()
        loaded = restored.q_networks[objective]
        assert original.keys() == loaded.keys()
        for key in original:
            assert torch.equal(original[key], loaded[key])


def test_provenance_travels_with_the_weights(tmp_path):
    """A checkpoint whose seeds have to be recovered from a path is not reproducible."""
    trainer = _trainer()
    payload = trainer.build_checkpoint_payload(episode=1, checkpoint_kind="final")
    restored = read_checkpoint(write_checkpoint(tmp_path / "c.pt", payload))

    assert restored.train_seed == trainer.train_seed
    assert restored.env_seed == trainer.env_seed
    assert restored.mobility_seed == trainer.mobility_seed
    assert restored.trainer_config["learning_rate"] == trainer.config.learning_rate
    assert restored.trainer_config["objective_weights"] == list(
        trainer.config.objective_weights
    ) or restored.trainer_config["objective_weights"] == trainer.config.objective_weights


def test_the_stored_config_reflects_the_W09_removals(tmp_path):
    trainer = _trainer()
    payload = trainer.build_checkpoint_payload(episode=1, checkpoint_kind="final")
    restored = read_checkpoint(write_checkpoint(tmp_path / "c.pt", payload))
    for removed in ("catfish_enabled", "anti_collapse_constraint_mode", "popart_enabled"):
        assert removed not in restored.trainer_config
    # And the corrected default is what gets frozen into the artifact.
    assert restored.trainer_config["epsilon_decay_episodes"] == 2000


def test_optimizers_can_be_omitted(tmp_path):
    trainer = _trainer()
    payload = trainer.build_checkpoint_payload(
        episode=1, checkpoint_kind="final", include_optimizers=False
    )
    restored = read_checkpoint(write_checkpoint(tmp_path / "c.pt", payload))
    assert restored.optimizers is None


# -- the version guard -----------------------------------------------------


def test_an_unknown_format_version_is_refused():
    """W-12 addition: the source reconstructs whatever version it is handed.

    A newer file would then load with fields silently absent — the wrong
    failure for the object that carries a trained policy.
    """
    payload = CheckpointPayloadV1(
        format_version=1,
        checkpoint_kind="final",
        episode=0,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        state_dim=125,
        action_dim=28,
        trainer_config={},
        checkpoint_rule=_rule(),
        q_networks=[{}],
        target_networks=[{}],
    ).to_dict()

    assert CheckpointPayloadV1.from_dict(payload).episode == 0

    payload["format_version"] = 2
    with pytest.raises(MCRLContractError, match="format version 2"):
        CheckpointPayloadV1.from_dict(payload)


def test_the_rule_records_whether_the_secondary_checkpoint_exists():
    """Honest absence beats a file that silently duplicates the final one."""
    rule = _rule()
    assert rule.secondary_implemented is False
    assert CheckpointRuleV1.from_dict(rule.to_dict()) == rule


def test_the_trainer_reports_its_own_rule():
    trainer = _trainer()
    rule = trainer.checkpoint_rule()
    assert rule.assumption_id == "ASSUME-MODQN-REP-015"
    assert rule.secondary_implemented is False
    assert "not-yet-implemented" in rule.secondary_status


# -- payloads are snapshots, not views ------------------------------------


def test_to_dict_deep_copies_so_a_payload_cannot_be_mutated_after_the_fact():
    config = {"nested": {"value": 1}}
    payload = CheckpointPayloadV1(
        format_version=1,
        checkpoint_kind="final",
        episode=0,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        state_dim=125,
        action_dim=28,
        trainer_config=config,
        checkpoint_rule=_rule(),
        q_networks=[{}],
        target_networks=[{}],
    )
    exported = payload.to_dict()
    exported["trainer_config"]["nested"]["value"] = 99
    assert payload.trainer_config["nested"]["value"] == 1


def test_mapping_access_is_supported_for_legacy_readers():
    payload = CheckpointPayloadV1(
        format_version=1,
        checkpoint_kind="final",
        episode=5,
        train_seed=1,
        env_seed=2,
        mobility_seed=3,
        state_dim=125,
        action_dim=28,
        trainer_config={},
        checkpoint_rule=_rule(),
        q_networks=[{}],
        target_networks=[{}],
    )
    assert payload["episode"] == 5
    assert payload.get("missing", "default") == "default"
    assert payload["checkpoint_rule"]["assumption_id"] == "ASSUME-MODQN-REP-015"


# -- end to end ------------------------------------------------------------


def test_save_and_restore_reproduces_the_policy(tmp_path):
    trainer = _trainer()
    states = torch.zeros(2, trainer.state_dim)
    with torch.no_grad():
        before = trainer.q_nets[0](states).clone()

    path = trainer.save_checkpoint(
        tmp_path / "final.pt", episode=1, checkpoint_kind="final"
    )

    with torch.no_grad():
        for parameter in trainer.q_nets[0].parameters():
            parameter.add_(1.0)
        perturbed = trainer.q_nets[0](states)
    assert not torch.allclose(before, perturbed)

    trainer.load_checkpoint(path)
    with torch.no_grad():
        after = trainer.q_nets[0](states)
    assert torch.allclose(before, after)
