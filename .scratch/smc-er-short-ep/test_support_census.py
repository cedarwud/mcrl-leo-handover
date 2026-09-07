from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("support_census", HERE / "support_census.py")
assert SPEC is not None and SPEC.loader is not None
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


class FakeState:
    def __init__(self, tick: int):
        self.tick = int(tick)


class FakeEnvironment:
    """Small state-only seam: no reward or successor outcome is exposed."""

    def __init__(self):
        self.environment = SimpleNamespace(
            _previous_association=[None],
            _candidates=SimpleNamespace(slot_tables=[object()]),
        )
        self._tick = 0

    def reset(self, _env_rng, _mobility_rng):
        self._tick = 0
        self.environment._previous_association = [None]
        self.environment._candidates = SimpleNamespace(slot_tables=[object()])
        return [FakeState(0)], [SimpleNamespace(mask=np.array([True]))], object()

    def step(self, _actions, _env_rng):
        self._tick += 1
        self.environment._candidates = SimpleNamespace(slot_tables=[object()])
        return SimpleNamespace(
            user_states=[FakeState(self._tick)],
            action_masks=[SimpleNamespace(mask=np.array([True]))],
        )


class FakeMain:
    def encode_states(self, states):
        return np.zeros((len(states), 1), dtype=np.float32)


def _authority():
    config = C.TrainerConfig(learning_rate=0.001, episodes=9000)
    return SimpleNamespace(
        checkpoint_payload=SimpleNamespace(trainer_config=asdict(config)),
        archive=object(),
        freeze_path=Path("freeze.json"),
        freeze_sha256="a" * 64,
        spec_path=Path("spec.md"),
        spec_sha256="b" * 64,
        implementation_hashes={},
        test_hashes={},
        census_implementation_hashes={},
        c1_corpus_path=Path("c1-manifest.json"),
        c1_corpus_sha256="f" * 64,
        prereg_path=Path("prereg.json"),
        prereg_sha256="c" * 64,
        tle_root=Path("tle"),
        tle_file_set_sha256="d" * 64,
        ephemeris={"archive": {"file_count": 373}},
        checkpoint_path=Path("checkpoint.pt"),
        checkpoint_sha256="e" * 64,
    )


def _run_with_supports(monkeypatch, *, c2_exposed, c3_exposed):
    monkeypatch.setattr(C, "main_greedy_actions", lambda *_args, **_kwargs: np.array([0]))

    def environment_factory(_archive, *, config, users):
        assert config.episodes == 9000
        assert users == 100
        return FakeEnvironment()

    def main_factory(_authority, *, users, config):
        assert users == 100
        assert config.episodes == 9000
        return FakeMain()

    def role_support(exposed):
        def support(*, states, main_actions, slot_tables, incumbents):
            del main_actions, slot_tables, incumbents
            return {0: (0, 1)} if exposed(states[0].tick) else {}

        return support

    return C.run_census(
        _authority(),
        environment_factory=environment_factory,
        main_factory=main_factory,
        c2_support_fn=role_support(c2_exposed),
        c3_support_fn=role_support(c3_exposed),
    )


def test_census_counts_exact_300_steps_and_passes_both_frozen_floors(monkeypatch):
    receipt = _run_with_supports(
        monkeypatch,
        # One exposed step at the start of each ten-step reset episode:
        # 3 pairs x 10 episodes = 30, exactly the frozen floor.
        c2_exposed=lambda tick: tick == 0,
        c3_exposed=lambda tick: tick == 0,
    )

    assert receipt["status"] == "PASS"
    assert receipt["schema"] == "multi-catfish-mcrl-v0.2-support-census-v2"
    assert receipt["authority"]["path_binding"] == "repository_relative_posix_v1"
    assert receipt["authority"]["tle_root_binding"] == "runtime_argument"
    assert "tle_root" not in receipt["authority"]
    assert receipt["authority"]["tle_file_count"] == 373
    assert all(
        not Path(receipt["authority"][field]).is_absolute()
        for field in (
            "freeze_manifest",
            "spec",
            "c1_exp_corpus_manifest",
            "canonical_prereg",
            "baseline_checkpoint",
        )
    )
    assert receipt["logical_steps"] == 300
    assert len(receipt["per_seed_pair"]) == 3
    assert all(row["logical_steps"] == 100 for row in receipt["per_seed_pair"])
    assert receipt["roles"]["C2"]["exposed_steps"] == 30
    assert receipt["roles"]["C3"]["exposed_steps"] == 30
    assert receipt["roles"]["C2"]["floor_pass"] is True
    assert receipt["roles"]["C3"]["floor_pass"] is True
    assert all(
        row["eligibility_inputs"]["reward_used"] is False
        and row["eligibility_inputs"]["successor_outcome_used"] is False
        and row["eligibility_inputs"]["counterfactual_used"] is False
        and row["eligibility_inputs"]["forecast_used"] is False
        and row["eligibility_inputs"]["specialist_outcome_used"] is False
        for row in receipt["per_seed_pair"][0]["steps"]
    )


def test_census_reports_scientific_no_go_when_one_role_misses_floor(monkeypatch):
    receipt = _run_with_supports(
        monkeypatch,
        c2_exposed=lambda _tick: False,
        c3_exposed=lambda tick: tick == 0,
    )

    assert receipt["status"] == "NO_GO"
    assert receipt["roles"]["C2"]["exposed_steps"] == 0
    assert receipt["roles"]["C2"]["floor_pass"] is False
    assert receipt["roles"]["C3"]["exposed_steps"] == 30
    assert receipt["roles"]["C3"]["floor_pass"] is True


def test_hash_failure_is_fail_closed(tmp_path):
    path = tmp_path / "input.bin"
    path.write_bytes(b"frozen input")
    with pytest.raises(C.CensusAuthorityError, match="hash mismatch"):
        C._assert_file_hash(path, "0" * 64, label="implementation input")


def test_census_authority_rejects_non_train_or_drifted_floor():
    with pytest.raises(C.CensusAuthorityError, match="TRAIN"):
        C._validate_census_block(
            {
                "partition": "test",
                "episodes_per_seed_pair": 10,
                "steps_per_episode": 10,
                "logical_steps_total": 300,
                "environment_mobility_seed_pairs": [list(pair) for pair in C.EXPECTED_SEED_PAIRS],
                "minimum_exposed_step_fraction_per_role": 0.1,
                "minimum_exposed_steps_per_role": 30,
                "reward_or_successor_used_for_eligibility": False,
            }
        )
    with pytest.raises(C.CensusAuthorityError, match="floor step count"):
        C._validate_census_block(
            {
                "partition": C.FROZEN_PARTITION_LABEL,
                "episodes_per_seed_pair": 10,
                "steps_per_episode": 10,
                "logical_steps_total": 300,
                "environment_mobility_seed_pairs": [list(pair) for pair in C.EXPECTED_SEED_PAIRS],
                "minimum_exposed_step_fraction_per_role": 0.1,
                "minimum_exposed_steps_per_role": 29,
                "reward_or_successor_used_for_eligibility": False,
            }
        )
