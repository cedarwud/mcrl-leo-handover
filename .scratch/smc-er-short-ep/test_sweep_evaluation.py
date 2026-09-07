from __future__ import annotations

import importlib.util
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "smc_er_sweep_evaluation", HERE / "sweep_evaluation.py"
)
assert SPEC is not None and SPEC.loader is not None
S = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def _row(
    *,
    arm="Full Multi-Catfish MCRL",
    train=1,
    seed=11,
    users=100,
    bits=100.0,
    energy=10.0,
):
    return S.EpisodeTotals(
        arm=arm,
        checkpoint_sha256="a" * 64,
        training_seed=train,
        evaluation_seed=seed,
        users=users,
        steps=10,
        duration_s=300.8,
        useful_bits=bits,
        system_energy_j=energy,
        system_ee_bits_per_j=bits / energy,
        mean_system_power_w=energy / 300.8,
        mean_system_throughput_bps=bits / 300.8,
        served_user_intervals=900,
        total_user_intervals=1000,
        served_fraction=0.9,
        zero_power_intervals=0,
        zero_service_intervals=0,
        r1_sum=1.0,
        r2_sum=-2.0,
        r3_sum=-3.0,
    )


def test_ratio_of_sums_is_not_mean_of_ratios():
    rows = [
        _row(seed=11, bits=100.0, energy=10.0),
        _row(seed=12, bits=100.0, energy=100.0),
    ]
    summary = S.aggregate_rows(rows)
    assert len(summary) == 1
    seed_row = summary[0]["seed_rows"][0]
    assert seed_row["system_ee_bits_per_j"] == pytest.approx(200.0 / 110.0)
    assert seed_row["system_ee_bits_per_j"] != pytest.approx((10.0 + 1.0) / 2.0)


def test_training_seeds_are_equal_weight_after_each_seed_pools_evaluation():
    rows = [
        _row(train=1, seed=11, bits=100.0, energy=10.0),
        _row(train=1, seed=12, bits=100.0, energy=10.0),
        _row(train=2, seed=11, bits=10.0, energy=10.0),
        _row(train=2, seed=12, bits=10.0, energy=10.0),
    ]
    summary = S.aggregate_rows(rows)[0]
    assert summary["training_seed_count"] == 2
    assert summary["mean_ee_bits_per_j"] == pytest.approx((10.0 + 1.0) / 2.0)


def test_ratio_of_sums_rejects_impossible_zero_energy():
    with pytest.raises(ValueError, match="positive useful bits"):
        S.ratio_of_sums(1.0, 0.0)


def test_aggregate_keeps_arm_and_user_points_separate():
    rows = [
        _row(arm="Baseline MODQN", users=60),
        _row(arm="Baseline MODQN", users=100),
        _row(arm="Full Multi-Catfish MCRL", users=60),
    ]
    summary = S.aggregate_rows(rows)
    assert {(row["arm"], row["users"]) for row in summary} == {
        ("Baseline MODQN", 60),
        ("Baseline MODQN", 100),
        ("Full Multi-Catfish MCRL", 60),
    }


def test_checkpoint_point_isolation_makes_seed_order_irrelevant(monkeypatch):
    """A prior held-out seed cannot contaminate the next point's runtime."""

    created = []

    class FakeEnvironment:
        def __init__(self):
            self.evaluations = 0

        def assert_ready_to_train(self):
            return None

    class FakeTrainer:
        def __init__(self, environment, *_args, **_kwargs):
            self.environment = environment
            self.loaded = None

        def load_checkpoint(self, checkpoint_path, *, load_optimizers):
            self.loaded = (Path(checkpoint_path), load_optimizers)

    payload = SimpleNamespace(
        trainer_config={}, train_seed=17, env_seed=23, mobility_seed=29
    )

    def fake_make_environment(_archive, *, users):
        assert users == 100
        environment = FakeEnvironment()
        created.append(environment)
        return environment

    def fake_evaluate(trainer, environment, **kwargs):
        assert trainer.environment is environment
        assert trainer.loaded == (Path("checkpoint.pt"), False)
        environment.evaluations += 1
        # This would become two if a prior seed reused the same environment.
        return _row(seed=kwargs["evaluation_seed"], bits=float(environment.evaluations))

    monkeypatch.setattr(S, "make_environment", fake_make_environment)
    monkeypatch.setattr(S, "MODQNTrainer", FakeTrainer)
    monkeypatch.setattr(S, "evaluate_one_episode", fake_evaluate)

    def run(seed):
        return S.evaluate_checkpoint_point(
            archive=object(),
            checkpoint_path=Path("checkpoint.pt"),
            checkpoint_payload=payload,
            arm="Full Multi-Catfish MCRL",
            checkpoint_sha256="b" * 64,
            users=100,
            evaluation_seed=seed,
        )

    only_111 = run(111)
    run(222)
    after_222_111 = run(111)
    repeat_111 = run(111)

    assert only_111 == after_222_111 == repeat_111
    assert len(created) == 4


def test_checkpoint_input_preflight_rejects_duplicate_arm_and_training_seed(
    monkeypatch, tmp_path
):
    checkpoint = tmp_path / "checkpoint.pt"
    checkpoint.write_bytes(b"test")
    payload = SimpleNamespace(train_seed=17)
    monkeypatch.setattr(S, "read_checkpoint", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(S, "sha256_file", lambda _path: "a" * 64)

    with pytest.raises(ValueError, match="duplicate \\(arm, training_seed\\)"):
        S._validated_checkpoint_inputs([
            ("Full Multi-Catfish MCRL", checkpoint),
            ("Full Multi-Catfish MCRL", checkpoint),
        ])


def test_checkpoint_input_preflight_rejects_missing_checkpoint():
    with pytest.raises(ValueError, match="checkpoint does not exist"):
        S._validated_checkpoint_inputs(
            [("Full Multi-Catfish MCRL", Path("missing.pt"))]
        )


def test_make_environment_uses_held_out_test_partition(monkeypatch):
    seen = {}

    monkeypatch.setattr(
        S, "ScenarioDriver", lambda archive, config: ("driver", archive, config)
    )
    monkeypatch.setattr(
        S.BlockAlternatingSplit,
        "for_archive",
        staticmethod(lambda archive: ("split", archive)),
    )

    class FakeSampler:
        @staticmethod
        def for_archive(archive, split, part):
            seen.update(archive=archive, split=split, part=part)
            return "sampler"

    monkeypatch.setattr(S, "EpisodeStartSampler", FakeSampler)
    monkeypatch.setattr(S, "StepEnvironment", lambda driver: ("step", driver))
    monkeypatch.setattr(
        S,
        "TrainerEnvironment",
        lambda environment, sampler: (environment, sampler),
    )

    archive = object()
    environment = S.make_environment(archive, users=3)

    assert seen == {
        "archive": archive,
        "split": ("split", archive),
        "part": S.TEST,
    }
    assert environment[1] == "sampler"


def test_sweep_rejects_noncanonical_prereg_before_loading_tle(tmp_path):
    fake = tmp_path / "prereg.json"
    fake.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="canonical sealed preregistration"):
        S.canonical_ephemeris_authority(fake, tmp_path / "tle")
