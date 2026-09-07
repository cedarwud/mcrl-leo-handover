"""W-87 -- the bounded post-GO V0.4 C3 consumer contract.

These tests deliberately exercise only the new consumer seams.  They do not
open TLE data, run an episode, or call the source/gate runners.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from mcrl.algorithms.ee_axis_action_shared import EEAxisActionSharedConfig
from mcrl.algorithms.ee_axis_action_shared_meanmax import (
    EEAxisMaskedMeanMaxConfig,
    EEAxisMaskedMeanMaxTrainer,
)
from mcrl.algorithms.ee_axis_pairwise import EEAxisPairBatch
from mcrl.algorithms.ee_axis_v04_hybrid import (
    EEAxisV04HybridTrainer,
    FrozenMeanMaxCheckpointSpec,
)


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / ".scratch" / "c3-v04" / "run_v04_c3_500_update_screen.py"
SEED = 2026092101
AUTHORITY = "a" * 64


def _module():
    spec = importlib.util.spec_from_file_location("v04_c3_screen_w87", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        + b"\n"
    )


def _write_json(path: Path, payload: object) -> str:
    encoded = _canonical(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    return hashlib.sha256(encoded).hexdigest()


def _gate_fixture(tmp_path: Path, runner, *, status: str | None = None) -> Path:
    gate = tmp_path / "gate"
    gate.mkdir(parents=True)
    digest = "b" * 64
    source = {
        "source_dir": "artifacts/fake-v04-source",
        "source_manifest_sha256": digest,
        "source_manifest_file_sha256": digest,
        "schedule_sha256": digest,
        "schedule_file_sha256": digest,
        "seed_split": {
            **{str(seed): "train" for seed in runner.TRAIN_SOURCE_SEEDS},
            **{str(seed): "validation" for seed in runner.VALIDATION_SOURCE_SEEDS},
        },
    }
    authority = {
        "schema": runner.AUTHORITY_SCHEMA,
        "status": "SEALED_BEFORE_VALIDATION_DATASET_AND_METRICS",
        "source": source,
        "source_manifest_sha256": digest,
        "source_seed_split": source["seed_split"],
        "train_source_seeds": list(runner.TRAIN_SOURCE_SEEDS),
        "validation_source_seeds": list(runner.VALIDATION_SOURCE_SEEDS),
        "test_source_seeds": [],
        "test_split_opened": False,
        "validation_dataset_bytes_opened": False,
        "validation_metrics_computed": False,
        "held_out_ee_evaluated": False,
        "training": False,
        "q3_pairwise_training_started": False,
        "episode_training_started": False,
        "episode_trajectory_opened": False,
        "source_schedule": {"schedule_sha256": digest},
        "gate_code_manifest": {},
    }
    authority["authority_sha256"] = runner.canonical_sha256(authority)
    authority_file_sha = _write_json(gate / "authority.json", authority)
    authority_seal_sha = _write_json(
        gate / "authority-seal.json",
        {
            "schema": runner.AUTHORITY_SEAL_SCHEMA,
            "authority_file_sha256": authority_file_sha,
            "authority_sha256": authority["authority_sha256"],
            "validation_dataset_bytes_opened": False,
            "validation_metrics_computed": False,
            "test_split_opened": False,
        },
    )

    selected = {}
    for seed in runner.INITIALIZATION_SEEDS:
        selected_path = gate / f"hybrid-{seed}.pt"
        selected_path.write_bytes(f"selected-{seed}".encode("ascii"))
        selected[str(seed)] = {
            "path": str(selected_path),
            "file_sha256": hashlib.sha256(selected_path.read_bytes()).hexdigest(),
            "strict_reload": True,
            "exact_three_networks": True,
            "frozen_q1_q2_bit_identical": True,
            "q1_head_index": 0,
            "q2_head_index": 1,
            "q3_trainable_only": True,
        }

    result = {
        "schema": runner.RESULT_SCHEMA,
        "status": status or runner.SUCCESS_STATUS,
        "claim_ceiling": runner.SUCCESS_CLAIM_CEILING,
        "authority_sha256": authority["authority_sha256"],
        "authority_file_sha256": authority_file_sha,
        "authority_seal_file_sha256": authority_seal_sha,
        "source_manifest_sha256": digest,
        "schedule_sha256": digest,
        "train_surface_sha256": digest,
        "test_split_opened": False,
        "held_out_ee_evaluated": False,
        "training": True,
        "training_scope": "Q3_PAIRWISE_LEARNABILITY_GATE_ONLY",
        "q3_pairwise_training_completed": True,
        "episode_training": False,
        "selected_q3_rung": 10,
        "selected_hybrids": selected,
    }
    result_file_sha = _write_json(gate / "result.json", result)
    _write_json(
        gate / "result-seal.json",
        {
            "schema": runner.RESULT_SEAL_SCHEMA,
            "result_file_sha256": result_file_sha,
            "authority_sha256": authority["authority_sha256"],
            "authority_file_sha256": authority_file_sha,
            "test_split_opened": False,
            "held_out_ee_evaluated": False,
        },
    )
    return gate


def _configs() -> tuple[EEAxisMaskedMeanMaxConfig, EEAxisActionSharedConfig]:
    common = {
        "state_dim": 228,
        "action_dim": 28,
        "hidden_layers": (5, 3),
        "activation": "tanh",
        "learning_rate": 0.01,
        "kappa_bits": 100.0,
        "beta": 0.1,
        "loss_weights": (1.0, 1.0, 1.0),
    }
    return EEAxisMaskedMeanMaxConfig(**common), EEAxisActionSharedConfig(**common)


def _hybrid(tmp_path: Path) -> EEAxisV04HybridTrainer:
    v03_config, v04_config = _configs()
    source = EEAxisMaskedMeanMaxTrainer(v03_config, train_seed=SEED)
    path = tmp_path / "init-rung-10.pt"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        torch.save(
            {
                "schema": "multi-catfish-mcrl-v03-e1-masked-meanmax-fallback-v1-checkpoint",
                "authority_sha256": AUTHORITY,
                "initialization_seed": SEED,
                "rung": 10,
                "validation_dataset_bytes_opened": True,
                "validation_metrics_computed": True,
                "test_split_opened": False,
                "held_out_ee_evaluated": False,
                "trainer": source.checkpoint_state(update_count=30),
            },
            path,
        )
    spec = FrozenMeanMaxCheckpointSpec(
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        authority_sha256=AUTHORITY,
        initialization_seed=SEED,
    )
    return EEAxisV04HybridTrainer.from_sealed_checkpoint(
        spec,
        v03_config=v03_config,
        v04_config=v04_config,
        selected_q3_rung=10,
    )


def _batch(rows: int = 4) -> EEAxisPairBatch:
    states = np.linspace(-0.7, 0.7, rows * 228, dtype=np.float32).reshape(rows, 228)
    return EEAxisPairBatch(
        states=states,
        reference_actions=np.zeros(rows, dtype=np.int64),
        candidate_actions=np.ones(rows, dtype=np.int64),
        target_surplus_bits=np.linspace(5.0, 25.0, rows, dtype=np.float64),
        action_masks=np.ones((rows, 28), dtype=np.bool_),
    )


def _row(*, policy: str, seed: int, init: int, update: int, bits: float, energy: float, served: int):
    return {
        "policy_label": policy,
        "evaluation_seed": seed,
        "initialization_seed": init,
        "checkpoint_update": update,
        "fading_field_sha256": "c" * 64,
        "steps": 10,
        "users": 100,
        "decision_count": 1000,
        "total_bits": bits,
        "total_energy_j": energy,
        "served_user_steps": served,
    }


def test_protocol_constants_pin_500_updates_checkpoints_train_seeds_and_no_test():
    runner = _module()
    assert runner.SCREEN_UPDATE_COUNT == 500
    assert runner.SCREEN_CHECKPOINT_UPDATES == (100, 200, 300, 400, 500)
    assert runner.PRIMARY_SCREEN_UPDATES == (0,)
    assert runner.EVALUATION_SCREEN_UPDATES == (0, 100, 200, 300, 400, 500)
    assert runner.SCREEN_UPDATE_UNIT == "additional_full_batch_C3_source_training_update"
    assert runner.PRIMARY_EVALUATION_ROLE == "PRIMARY_SELECTED_GATE_RUNG"
    assert runner.EXPLORATORY_EVALUATION_ROLE == "EXPLORATORY_TREND_CHECKPOINT"
    assert runner.EVALUATION_SEEDS == tuple(range(2026092401, 2026092411))
    assert runner.EVALUATION_SPLIT == "TRAIN"
    assert runner.TEST_SPLIT_OPENED is False


def test_gate_authentication_requires_go_status_and_binds_selected_artifact_hashes(
    tmp_path: Path,
):
    runner = _module()
    gate = _gate_fixture(tmp_path, runner)
    receipt = runner.authenticate_gate(gate)
    assert receipt["status"] == runner.SUCCESS_STATUS
    assert receipt["selected_q3_rung"] == 10
    assert set(receipt["selected_hybrid_paths"]) == set(
        str(seed) for seed in runner.INITIALIZATION_SEEDS
    )

    stopped = _gate_fixture(tmp_path / "stopped", runner, status="STOP_V04_C3")
    with pytest.raises(runner.V04C3ScreenError, match="GO_500EP_SCREEN_ONLY"):
        runner.authenticate_gate(stopped)

    selected = gate / f"hybrid-{runner.INITIALIZATION_SEEDS[0]}.pt"
    selected.write_bytes(b"drifted")
    with pytest.raises(runner.V04C3ScreenError, match="selected hybrid.*SHA"):
        runner.authenticate_gate(gate)


def test_update_screen_runs_exactly_500_full_batch_calls_and_checkpoints_every_100():
    runner = _module()

    class FakeTrainer:
        def __init__(self):
            self.q3_update_count = 0

        def update_c3(self, batch):
            assert batch == "full-train-batch"
            self.q3_update_count += 1
            return {"route": "C3", "update_count": self.q3_update_count}

    trainer = FakeTrainer()
    checkpoints = []
    metrics = runner.run_c3_update_screen(
        trainer,
        "full-train-batch",
        on_checkpoint=lambda count, _trainer: checkpoints.append(count),
    )
    assert len(metrics) == 500
    assert trainer.q3_update_count == 500
    assert checkpoints == [100, 200, 300, 400, 500]


def test_screen_reload_allows_gate_rung_plus_updates_but_receipts_freeze_q1_q2(
    tmp_path: Path,
):
    runner = _module()
    trainer = _hybrid(tmp_path)
    for _ in range(15):
        trainer.update_c3(_batch())
    state = trainer.checkpoint_state()
    frozen = [copy.deepcopy(network.state_dict()) for network in trainer.q_nets[:2]]

    # The V0.3 lineage includes the canonical checkpoint path, so a reload
    # must reconstruct Q1/Q2 from that same sealed source artifact.
    restored = _hybrid(tmp_path)
    assert (
        runner.restore_screen_hybrid_state(
            restored,
            state,
            gate_selected_q3_rung=10,
            screen_updates_completed=5,
        )
        == 15
    )
    assert restored.q3_update_count == 15
    for before, network in zip(frozen, restored.q_nets[:2], strict=True):
        assert all(torch.equal(before[name], network.state_dict()[name]) for name in before)

    drifted = copy.deepcopy(state)
    drifted["q_networks"][0][next(iter(drifted["q_networks"][0]))].view(-1)[0] += 1.0
    with pytest.raises(runner.V04C3ScreenError, match="frozen-head tensor drifted"):
        runner.restore_screen_hybrid_state(
            restored,
            drifted,
            gate_selected_q3_rung=10,
            screen_updates_completed=5,
        )


def test_pooled_ratio_of_sums_and_zero_loss_service_guard_are_explicit():
    runner = _module()
    full = [
        _row(policy="FULL", seed=1, init=11, update=100, bits=10.0, energy=2.0, served=8),
        _row(policy="FULL", seed=2, init=11, update=100, bits=20.0, energy=5.0, served=7),
    ]
    drop = [
        _row(policy="DROP_C3", seed=1, init=11, update=100, bits=9.0, energy=1.0, served=8),
        _row(policy="DROP_C3", seed=2, init=11, update=100, bits=20.0, energy=4.0, served=6),
    ]
    summary = runner.aggregate_policy_rows(full)
    assert summary["pooled_ratio_of_sums_ee_bits_per_j"] == pytest.approx(30.0 / 7.0)
    guard = runner.enforce_zero_loss_service_guard(full, drop)
    assert guard["pass"] is True
    assert guard["per_pair_pass"] is True
    assert guard["pooled_pass"] is True

    drop[1]["served_user_steps"] = 8
    failed_guard = runner.enforce_zero_loss_service_guard(full, drop)
    assert failed_guard["pass"] is False
    assert failed_guard["per_pair_pass"] is False
    assert failed_guard["pooled_pass"] is False
    assert failed_guard["violations"]


def test_primary_selected_rung_is_zero_update_ee_evaluation_and_guard_failure_is_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runner = _module()
    trainer = _hybrid(tmp_path)
    trainer.q3_update_count = 10
    gate_receipt = {"selected_q3_rung": 10, "authority_sha256": AUTHORITY}

    def fake_episode(_trainer, _archive, *, gate_authority_sha256, initialization_seed,
                     checkpoint_update, evaluation_seed, drop_c3,
                     gate_selected_q3_rung, total_q3_update_count, evaluation_role):
        policy = "DROP_C3" if drop_c3 else "FULL"
        served = 9 if drop_c3 else 8
        return {
            **_row(
                policy=policy,
                seed=evaluation_seed,
                init=initialization_seed,
                update=checkpoint_update,
                bits=10.0,
                energy=2.0,
                served=served,
            ),
            "gate_selected_q3_rung": gate_selected_q3_rung,
            "screen_updates_completed": checkpoint_update,
            "total_q3_update_count": total_q3_update_count,
            "evaluation_role": evaluation_role,
            "screen_update_unit": runner.SCREEN_UPDATE_UNIT,
            "held_out_ee_evaluated": True,
            "test_split_opened": False,
        }

    monkeypatch.setattr(runner, "evaluate_v04_episode", fake_episode)
    matched = runner.evaluate_matched_checkpoint(
        trainer,
        object(),
        gate_receipt=gate_receipt,
        initialization_seed=SEED,
        checkpoint_update=0,
    )
    assert matched["screen_updates_completed"] == 0
    assert matched["gate_selected_q3_rung"] == 10
    assert matched["total_q3_update_count"] == 10
    assert matched["evaluation_role"] == runner.PRIMARY_EVALUATION_ROLE
    assert matched["held_out_ee_evaluated"] is True
    assert matched["service_guard"]["pass"] is False
    assert matched["service_guard"]["violations"]


def test_run_screen_publishes_primary_receipt_before_any_source_update(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runner = _module()
    events: list[tuple[str, object]] = []
    digest = "d" * 64
    gate_receipt = {
        "authority_sha256": "a" * 64,
        "result_file_sha256": "b" * 64,
        "source_manifest_sha256": "c" * 64,
        "schedule_sha256": "e" * 64,
        "train_surface_sha256": "f" * 64,
        "selected_q3_rung": 100,
    }

    monkeypatch.setattr(runner, "authenticate_gate", lambda *args, **kwargs: gate_receipt)
    monkeypatch.setattr(
        runner,
        "load_train_c3_batch",
        lambda *args, **kwargs: ("full-train-batch", gate_receipt["train_surface_sha256"]),
    )
    monkeypatch.setattr(runner, "read_prereg", lambda *args, **kwargs: object())
    monkeypatch.setattr(runner, "_frozen_archive", lambda *args, **kwargs: object())

    def fake_eval(_archive, **kwargs):
        update = kwargs["screen_updates_completed"]
        events.append(("evaluate", update))
        return {
            "screen_updates_completed": update,
            "gate_selected_q3_rung": 100,
            "total_q3_update_count": 100 + update,
            "held_out_ee_evaluated": True,
            "service_guard": {"pass": True},
        }

    monkeypatch.setattr(runner, "_evaluate_checkpoint_set", fake_eval)

    def fake_write(path, payload):
        events.append(("write", Path(path).name))
        return digest

    monkeypatch.setattr(runner, "_write_once_json", fake_write)

    def fake_train(**kwargs):
        events.append(("train", 500))
        return {"screen_updates": 500}

    monkeypatch.setattr(runner, "_train_and_checkpoint", fake_train)
    result = runner.run_screen(output_dir=tmp_path / "screen")

    assert result["status"] == "SCREEN_COMPLETE"
    assert events[0] == ("evaluate", 0)
    assert events[1] == ("write", "primary-evaluation.json")
    assert events[2] == ("train", 500)
    assert [update for kind, update in events if kind == "evaluate"] == [0, 100, 200, 300, 400, 500]
    assert result["primary_screen_updates_completed"] == 0
    assert result["held_out_ee_evaluated"] is True


def test_checkpoint_metadata_separates_gate_rung_screen_updates_and_total_count(
    tmp_path: Path,
):
    runner = _module()
    trainer = _hybrid(tmp_path)
    # The actual update loop is covered separately; this test isolates the
    # distinction between the selected gate rung, added screen updates, and
    # the absolute Q3 update count written into a checkpoint receipt.
    trainer.q3_update_count = 110
    receipt = {
        "selected_q3_rung": 10,
        "authority_sha256": AUTHORITY,
        "result_file_sha256": "b" * 64,
        "source_manifest_sha256": "b" * 64,
        "schedule_sha256": "b" * 64,
    }
    payload = runner.build_screen_checkpoint_payload(
        trainer,
        receipt,
        source_surface_sha256="c" * 64,
        screen_updates_completed=100,
    )
    assert payload["gate_selected_q3_rung"] == 10
    assert payload["screen_updates_completed"] == 100
    assert payload["total_q3_update_count"] == 110
    assert payload["screen_update_unit"] == runner.SCREEN_UPDATE_UNIT


def test_missing_gate_result_reports_exact_artifact_and_never_invents_a_checkpoint(
    tmp_path: Path,
):
    runner = _module()
    with pytest.raises(runner.V04C3ScreenError, match="result.json") as caught:
        runner.authenticate_gate(tmp_path / "not-published")
    assert "gate result" in str(caught.value)
