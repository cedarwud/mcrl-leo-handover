"""W-30 — orchestration follows the corrected freeze without a long run."""

from __future__ import annotations

import datetime as dt
import json
from types import SimpleNamespace

import numpy as np
import pytest

from mcrl.errors import P6NonFiniteEvaluationError
from mcrl.runtime.prereg import read_prereg
from mcrl.runtime.probe_p6 import P6_EVALUATION_SEEDS, P6_LEARNING_RATES
from mcrl.runtime import training_pipeline as pipeline
from mcrl.runtime import reward_calibration
from mcrl.runtime.trainer_spec import CollapseSample, EpisodeLog, TrainerConfig


@pytest.fixture(scope="module")
def record():
    return read_prereg(pipeline.CANONICAL_PREREG)


def test_frozen_p6_matches_the_launcher_and_builds_an_explicit_lr_config(record):
    p6 = pipeline.assert_p6_protocol_matches_record(record)
    config = pipeline._trainer_config(record, learning_rate=0.003)

    assert p6["sweep"]["learning_rate"] == list(P6_LEARNING_RATES)
    assert config.learning_rate == pytest.approx(0.003)
    assert config.episodes == 9000
    assert config.device == "cpu"


def test_protocol_guard_includes_matched_and_main_seed_sets(
    monkeypatch, record
):
    monkeypatch.setattr(pipeline, "P6_TRAIN_SEED", 123)

    with pytest.raises(pipeline.MCRLContractError, match="disagrees"):
        pipeline.assert_p6_protocol_matches_record(record)


def test_trainer_config_reads_reward_scales_from_the_frozen_mapping(
    monkeypatch, record
):
    monkeypatch.setattr(reward_calibration, "REWARD_SCALES", (9.0, 9.0, 9.0))

    config = pipeline._trainer_config(record, learning_rate=0.003)

    assert config.reward_calibration_enabled is True
    assert config.reward_calibration_scales == pytest.approx(
        (2029238.4328742754, 1.0, 6.0)
    )


def test_corrective_refreeze_gate_accepts_the_recorded_probe_bundle(record):
    accepted = pipeline.assert_corrective_probe_refreeze(record)

    assert accepted["status"] == "corrective-refreeze-accepted"
    assert accepted["c1"] == 2029238.4328742754
    assert accepted["c3"] == 6


def test_corrective_refreeze_gate_rejects_a_different_summary_path(
    tmp_path, record
):
    with pytest.raises(
        pipeline.MCRLContractError, match="not the R2-recorded artifact"
    ):
        pipeline.assert_corrective_probe_refreeze(
            record, tmp_path / "summary.json"
        )


def test_corrective_refreeze_gate_rejects_a_mapping_not_equal_to_raw_p95(record):
    import copy

    from mcrl.runtime.prereg import PreregRecord

    sections = copy.deepcopy(record.sections)
    sections["selection_mappings"]["Q-F c1 calibration scale"]["resolved"] = (
        2029238.433
    )
    tampered = PreregRecord(
        sections=sections,
        holdout=record.holdout,
        schema=record.schema,
    ).with_digest()

    with pytest.raises(pipeline.MCRLContractError, match="does not exactly apply"):
        pipeline.assert_corrective_probe_refreeze(tampered)


def test_corrective_refreeze_gate_rejects_an_unrelated_rehashed_edit(record):
    import copy

    from mcrl.runtime.prereg import PreregRecord

    sections = copy.deepcopy(record.sections)
    sections["thresholds"]["outage_dropped_transition_rate"]["value"] = 0.5
    tampered = PreregRecord(
        sections=sections,
        holdout=record.holdout,
        schema=record.schema,
    ).with_digest()

    with pytest.raises(pipeline.MCRLContractError, match="canonical R2 digest"):
        pipeline.assert_corrective_probe_refreeze(tampered)


def test_ephemeris_guard_rejects_a_live_tle_hash_drift(record):
    frozen = record.sections["ephemeris"]

    class FrozenRowsArchive:
        root = pipeline.Path("/portable/tle")
        dates = tuple(
            dt.date.fromisoformat(row["date"])
            for row in frozen["frozen_files"]
        )

        @property
        def date_range(self):
            return self.dates[0], self.dates[-1]

        def manifest_rows(self, _dates):
            return [dict(row) for row in frozen["frozen_files"]]

    archive = FrozenRowsArchive()
    live = pipeline.assert_ephemeris_matches_record(
        record,
        archive=archive,
        sgp4_contract=dict(frozen["sgp4"]),
    )
    assert live["file_set_sha256"] == frozen["file_set_sha256"]

    original = archive.manifest_rows

    def drifted_rows(dates):
        rows = original(dates)
        rows[0]["sha256"] = "0" * 64
        return rows

    archive.manifest_rows = drifted_rows
    with pytest.raises(pipeline.MCRLContractError, match="ephemeris"):
        pipeline.assert_ephemeris_matches_record(
            record,
            archive=archive,
            sgp4_contract=dict(frozen["sgp4"]),
        )


def test_run_fingerprint_changes_when_source_bytes_change(tmp_path, record):
    source = tmp_path / "worker.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    first = pipeline.build_run_fingerprint(
        record,
        role="P6-learning-rate-arm",
        learning_rate=0.003,
        train_seed=pipeline.P6_TRAIN_SEED,
        env_seed=pipeline.P6_ENV_SEED,
        mobility_seed=pipeline.P6_MOBILITY_SEED,
        code_paths=[source],
        dependency_versions={"python": "test"},
    )

    source.write_text("VALUE = 2\n", encoding="utf-8")
    second = pipeline.build_run_fingerprint(
        record,
        role="P6-learning-rate-arm",
        learning_rate=0.003,
        train_seed=pipeline.P6_TRAIN_SEED,
        env_seed=pipeline.P6_ENV_SEED,
        mobility_seed=pipeline.P6_MOBILITY_SEED,
        code_paths=[source],
        dependency_versions={"python": "test"},
    )

    assert first["code_sha256"] != second["code_sha256"]
    assert first["fingerprint_sha256"] != second["fingerprint_sha256"]


def test_nominally_complete_arm_without_artifacts_is_not_reusable(
    tmp_path, record
):
    fingerprint = pipeline.build_run_fingerprint(
        record,
        role="P6-learning-rate-arm",
        learning_rate=0.003,
        train_seed=pipeline.P6_TRAIN_SEED,
        env_seed=pipeline.P6_ENV_SEED,
        mobility_seed=pipeline.P6_MOBILITY_SEED,
        code_paths=[],
        dependency_versions={"python": "test"},
    )
    candidate = {
        "status": "complete",
        "role": "P6-learning-rate-arm",
        "learning_rate": 0.003,
        "prereg_digest": record.digest,
        "run_fingerprint": fingerprint,
        "calibrated_scalar_reward_by_seed": [1.0] * len(P6_EVALUATION_SEEDS),
    }

    assert not pipeline.arm_status_is_reusable(
        candidate,
        tmp_path,
        expected_fingerprint=fingerprint,
        expected_episodes=9000,
        evaluate_p6=True,
    )


def test_arm_persists_failed_status_for_an_unexpected_exception(
    monkeypatch, tmp_path, record
):
    monkeypatch.setattr(
        pipeline,
        "make_training_environment",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("environment boom")),
    )

    with pytest.raises(RuntimeError, match="environment boom"):
        pipeline._run_training(
            record=record,
            learning_rate=0.003,
            output_dir=tmp_path,
            role="P6-learning-rate-arm",
            train_seed=pipeline.P6_TRAIN_SEED,
            env_seed=pipeline.P6_ENV_SEED,
            mobility_seed=pipeline.P6_MOBILITY_SEED,
            evaluate_p6=True,
        )

    status = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    assert status["failure_stage"] == "environment-setup"
    assert status["error_type"] == "RuntimeError"


def test_pipeline_persists_p6_failure_instead_of_leaving_running_status(
    monkeypatch, tmp_path, record
):
    monkeypatch.setattr(
        pipeline, "validate_server_setup", lambda _path, **_kwargs: record
    )
    monkeypatch.setattr(
        pipeline,
        "run_p6_sweep",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("P6 boom")),
    )

    with pytest.raises(RuntimeError, match="P6 boom"):
        pipeline.run_training_pipeline(pipeline.CANONICAL_PREREG, tmp_path)

    status = json.loads(
        (tmp_path / "pipeline-status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "failed"
    assert status["phase"] == "P6"
    assert status["error_type"] == "RuntimeError"


def test_pipeline_persists_validation_failure(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(
        pipeline,
        "validate_server_setup",
        lambda _path, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("validation boom")
        ),
    )

    with pytest.raises(RuntimeError, match="validation boom"):
        pipeline.run_training_pipeline(pipeline.CANONICAL_PREREG, tmp_path)

    status = json.loads(
        (tmp_path / "pipeline-status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "failed"
    assert status["phase"] == "validation"
    assert status["error_type"] == "RuntimeError"


def test_pipeline_never_calls_a_noncomplete_main_result_complete(
    monkeypatch, tmp_path, record
):
    monkeypatch.setattr(
        pipeline, "validate_server_setup", lambda _path, **_kwargs: record
    )
    monkeypatch.setattr(
        pipeline,
        "run_p6_sweep",
        lambda *_args: (0.003, {"status": "complete"}),
    )
    monkeypatch.setattr(
        pipeline,
        "run_main_training",
        lambda *_args, **_kwargs: {"status": "nonfinite"},
    )

    with pytest.raises(pipeline.MCRLContractError, match="main training"):
        pipeline.run_training_pipeline(pipeline.CANONICAL_PREREG, tmp_path)

    status = json.loads(
        (tmp_path / "pipeline-status.json").read_text(encoding="utf-8")
    )
    assert status["status"] == "failed"
    assert status["phase"] == "main"


def test_arm_rerun_resumes_from_the_last_atomic_episode_boundary(
    monkeypatch, tmp_path, record
):
    config = TrainerConfig(
        hidden_layers=(4,),
        learning_rate=0.003,
        batch_size=1,
        replay_capacity=4,
        episodes=2,
        target_update_every_episodes=1,
        epsilon_decay_episodes=1,
    )
    starts: list[int] = []
    loaded_states: list[dict] = []
    instances: list[object] = []

    sample = CollapseSample(
        q_margin=0.1,
        q_entropy=0.2,
        q_margin_raw=0.3,
        q_range=1.0,
        active_beam_count=1.0,
        argmax_agreement=1.0,
        active_beam_count_executed=1.0,
        argmax_agreement_executed=1.0,
    )

    def make_log(episode):
        return EpisodeLog(
            episode=episode,
            epsilon=0.1,
            r1_mean=1.0,
            r2_mean=0.0,
            r3_mean=0.0,
            scalar_reward=0.5,
            total_handovers=0,
            replay_size=episode + 1,
            collapse_first=sample,
            collapse_last=sample,
            r1_mean_calibrated=1.0,
        )

    class Environment:
        @staticmethod
        def assert_ready_to_train():
            return None

    class FakeTrainer:
        def __init__(self, *_args, **_kwargs):
            self.progress = 0
            instances.append(self)

        def training_state_dict(self):
            return {"progress": self.progress}

        def load_training_state_dict(self, state):
            loaded_states.append(dict(state))
            self.progress = int(state["progress"])

        def train(
            self,
            *,
            progress_every,
            start_episode,
            initial_logs,
            episode_callback,
        ):
            del progress_every
            starts.append(start_episode)
            logs = list(initial_logs)
            for episode in range(start_episode, config.episodes):
                self.progress = episode + 1
                log = make_log(episode)
                logs.append(log)
                episode_callback(log)
                if len(instances) == 1:
                    raise RuntimeError("interrupt after durable boundary")
            return logs

        @staticmethod
        def save_checkpoint(path, **_kwargs):
            path.write_bytes(b"test checkpoint")

    monkeypatch.setattr(pipeline, "RESUME_EVERY_EPISODES", 1)
    monkeypatch.setattr(pipeline, "make_training_environment", lambda **_kwargs: Environment())
    monkeypatch.setattr(pipeline, "_trainer_config", lambda *_args, **_kwargs: config)
    monkeypatch.setattr(pipeline, "MODQNTrainer", FakeTrainer)

    kwargs = {
        "record": record,
        "learning_rate": 0.003,
        "output_dir": tmp_path,
        "role": "main-training",
        "train_seed": pipeline.MAIN_TRAIN_SEED,
        "env_seed": pipeline.MAIN_ENV_SEED,
        "mobility_seed": pipeline.MAIN_MOBILITY_SEED,
        "evaluate_p6": False,
    }
    with pytest.raises(RuntimeError, match="durable boundary"):
        pipeline._run_training(**kwargs)

    result = pipeline._run_training(**kwargs)

    assert starts == [0, 1]
    assert loaded_states == [{"progress": 1}]
    assert result["status"] == "complete"
    assert result["episodes_completed"] == 2


def test_collapse_summary_uses_the_frozen_tail_1000_median():
    def make_log(episode: int, value: float) -> EpisodeLog:
        sample = CollapseSample(
            q_margin=value,
            q_entropy=value,
            q_margin_raw=value,
            q_range=1.0,
            active_beam_count=value,
            argmax_agreement=value,
            active_beam_count_executed=value,
            argmax_agreement_executed=value,
        )
        return EpisodeLog(
            episode=episode,
            epsilon=0.01,
            r1_mean=1.0,
            r2_mean=0.0,
            r3_mean=0.0,
            scalar_reward=0.0,
            total_handovers=0,
            replay_size=episode + 1,
            collapse_first=sample,
            collapse_last=sample,
        )

    # The first row lies outside the frozen tail.  A tail-100 mean would be
    # 0.99, whereas the required tail-1000 median is exactly 0.5.
    logs = [make_log(0, 99.0)] + [
        make_log(episode, 0.0 if episode <= 500 else 1.0)
        for episode in range(1, 1001)
    ]

    summary = pipeline._collapse_summary(logs)

    assert summary is not None
    assert summary["tail_window"] == 1000
    assert summary["aggregation"] == "median"
    assert summary["first"]["active_beam_count"] == pytest.approx(0.5)


def test_nonfinite_p6_evaluation_marks_only_that_arm_incomplete(
    monkeypatch, tmp_path, record
):
    config = TrainerConfig(
        hidden_layers=(4,),
        learning_rate=0.003,
        batch_size=1,
        replay_capacity=4,
        episodes=1,
        target_update_every_episodes=1,
        epsilon_decay_episodes=1,
    )
    sample = CollapseSample(
        q_margin=0.1,
        q_entropy=0.2,
        q_margin_raw=0.3,
        q_range=1.0,
        active_beam_count=1.0,
        argmax_agreement=1.0,
        active_beam_count_executed=1.0,
        argmax_agreement_executed=1.0,
    )
    log = EpisodeLog(
        episode=0,
        epsilon=0.1,
        r1_mean=1.0,
        r2_mean=0.0,
        r3_mean=0.0,
        scalar_reward=0.5,
        total_handovers=0,
        replay_size=1,
        collapse_first=sample,
        collapse_last=sample,
        r1_mean_calibrated=1.0,
    )

    class Environment:
        @staticmethod
        def assert_ready_to_train():
            return None

    class FakeTrainer:
        def __init__(self, *_args, **_kwargs):
            pass

        def train(self, *, episode_callback, **_kwargs):
            episode_callback(log)
            return [log]

        @staticmethod
        def save_checkpoint(path, **_kwargs):
            path.write_bytes(b"test checkpoint")

    monkeypatch.setattr(pipeline, "make_training_environment", lambda **_kwargs: Environment())
    monkeypatch.setattr(pipeline, "_trainer_config", lambda *_args, **_kwargs: config)
    monkeypatch.setattr(pipeline, "MODQNTrainer", FakeTrainer)
    monkeypatch.setattr(
        pipeline,
        "evaluate_p6_arm",
        lambda *_args: (_ for _ in ()).throw(
            P6NonFiniteEvaluationError("non-finite final policy")
        ),
    )

    result = pipeline._run_training(
        record=record,
        learning_rate=0.003,
        output_dir=tmp_path,
        role="P6-learning-rate-arm",
        train_seed=pipeline.P6_TRAIN_SEED,
        env_seed=pipeline.P6_ENV_SEED,
        mobility_seed=pipeline.P6_MOBILITY_SEED,
        evaluate_p6=True,
    )

    assert result["status"] == "incomplete"
    assert result["failure_kind"] == "nonfinite-evaluation"
    assert result["episodes_completed"] == 1


def test_p6_diagnostics_do_not_disqualify_a_finite_single_action_policy():
    class SingleActionEnvironment:
        num_users = 1

        def reset(self, _env_rng, _mobility_rng):
            return (
                [object()],
                [SimpleNamespace(mask=np.array([True], dtype=bool))],
                None,
            )

        def step(self, _actions, _env_rng):
            return SimpleNamespace(
                done=True,
                user_states=[object()],
                action_masks=[SimpleNamespace(mask=np.array([True], dtype=bool))],
            )

    class FiniteTrainer:
        config = TrainerConfig()

        @staticmethod
        def encode_states(_states):
            return np.zeros((1, 1), dtype=np.float32)

        @staticmethod
        def scalarized_q_values(_encoded):
            return np.array([[1.0]], dtype=np.float64)

        @staticmethod
        def reward_vector_from_step_result(_result, _uid, *, is_eval=False):
            assert is_eval
            return np.array([1.0, 0.0, 0.0], dtype=np.float64)

    result = pipeline.evaluate_p6_arm(
        FiniteTrainer(),
        SingleActionEnvironment,
    )

    assert len(result["calibrated_scalar_reward_by_seed"]) == len(
        P6_EVALUATION_SEEDS
    )
    assert result["perturbation_diagnostic_available"] is False
    assert result["perturbation_greedy_action_retention"] is None
    assert result["perturbation_kendall_tau"] is None


def test_p6_nonfinite_policy_is_a_typed_evaluation_failure():
    class Environment:
        num_users = 1

        def reset(self, _env_rng, _mobility_rng):
            return (
                [object()],
                [SimpleNamespace(mask=np.array([True], dtype=bool))],
                None,
            )

    class NonFiniteTrainer:
        config = TrainerConfig()

        @staticmethod
        def encode_states(_states):
            return np.zeros((1, 1), dtype=np.float32)

        @staticmethod
        def scalarized_q_values(_encoded):
            return np.array([[np.nan]], dtype=np.float64)

    with pytest.raises(P6NonFiniteEvaluationError):
        pipeline.evaluate_p6_arm(NonFiniteTrainer(), Environment)


def test_p6_nonfinite_reward_is_a_typed_evaluation_failure():
    class Environment:
        num_users = 1

        def reset(self, _env_rng, _mobility_rng):
            return (
                [object()],
                [SimpleNamespace(mask=np.array([True], dtype=bool))],
                None,
            )

        def step(self, _actions, _env_rng):
            return SimpleNamespace(done=True, user_states=[], action_masks=[])

    class NonFiniteRewardTrainer:
        config = TrainerConfig()

        @staticmethod
        def encode_states(_states):
            return np.zeros((1, 1), dtype=np.float32)

        @staticmethod
        def scalarized_q_values(_encoded):
            return np.array([[1.0]], dtype=np.float64)

        @staticmethod
        def reward_vector_from_step_result(_result, _uid, *, is_eval=False):
            assert is_eval
            return np.array([np.nan, 0.0, 0.0], dtype=np.float64)

    with pytest.raises(P6NonFiniteEvaluationError, match="reward"):
        pipeline.evaluate_p6_arm(NonFiniteRewardTrainer(), Environment)


def test_p6_sweep_runs_declared_order_and_selects_only_by_mean(
    monkeypatch, tmp_path, record
):
    calls: list[float] = []

    def fake_run_training(**kwargs):
        learning_rate = float(kwargs["learning_rate"])
        calls.append(learning_rate)
        if learning_rate == 0.01:
            return {
                "status": "nonfinite",
                "learning_rate": learning_rate,
                "prereg_digest": record.digest,
            }
        scores = (
            [0.0] * 9 + [100.0]
            if learning_rate == 0.003
            else [9.0] * len(P6_EVALUATION_SEEDS)
        )
        return {
            "status": "complete",
            "learning_rate": learning_rate,
            "prereg_digest": record.digest,
            "calibrated_scalar_reward_by_seed": scores,
            # The losing diagnostic cannot overturn the higher primary mean.
            "perturbation_greedy_action_retention": (
                0.01 if learning_rate == 0.003 else 1.0
            ),
        }

    monkeypatch.setattr(pipeline, "_run_training", fake_run_training)

    selected, summary = pipeline.run_p6_sweep(record, tmp_path)

    assert calls == list(P6_LEARNING_RATES)
    assert selected == pytest.approx(0.003)
    assert summary["selection"]["selected_learning_rate"] == pytest.approx(0.003)
    assert (tmp_path / "p6-summary.json").exists()


def test_pipeline_enters_main_only_with_the_p6_selected_learning_rate(
    monkeypatch, tmp_path, record
):
    calls: list[tuple[str, float | None]] = []

    monkeypatch.setattr(
        pipeline,
        "validate_server_setup",
        lambda _path, **_kwargs: record,
    )

    def fake_p6(_record, _output_dir):
        calls.append(("P6", None))
        return 0.001, {"status": "complete"}

    def fake_main(_record, _output_dir, *, learning_rate):
        calls.append(("main", float(learning_rate)))
        return {
            "status": "complete",
            "learning_rate": float(learning_rate),
            "prereg_digest": record.digest,
        }

    monkeypatch.setattr(pipeline, "run_p6_sweep", fake_p6)
    monkeypatch.setattr(pipeline, "run_main_training", fake_main)

    result = pipeline.run_training_pipeline(
        pipeline.CANONICAL_PREREG,
        tmp_path,
    )

    assert calls == [("P6", None), ("main", 0.001)]
    assert result["selected_learning_rate"] == pytest.approx(0.001)
    status = json.loads(
        (tmp_path / "pipeline-status.json").read_text(encoding="utf-8")
    )
    assert status["phase"] == "complete"
    assert status["main"]["learning_rate"] == pytest.approx(0.001)
