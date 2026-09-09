from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_v023_c1c2_successor_world_plan as builder
import v023_c1c2_successor_physical_runner as runner
from mcrl.runtime.trainer_env import TrainerEnvironment


def _plan() -> runner.EvaluationPlan:
    payload = builder.build_world_plan()
    return runner.EvaluationPlan(
        worlds=tuple(runner.WorldBinding(**row) for row in payload["worlds"]),
        plan_sha256=payload["plan_sha256"],
    )


class _StubEvaluationAdapter:
    """The predecessor runner's deterministic persistence helper, generalized."""

    def __init__(self) -> None:
        self._bindings = {
            arm: {
                "arm": arm,
                "routes": [] if arm == "BASELINE" else ["C1", "C2"],
                "checkpoint_sha256": runner.canonical_sha256({"arm": arm}),
                "fixed_policy": True,
            }
            for arm in runner.ARMS
        }
        self._states: dict[str, dict[str, object] | None] = {
            arm: None for arm in runner.ARMS
        }

    @property
    def policy_bindings(self):
        return self._bindings

    def resume_state_for(self, arm: str):
        return self._states[arm]

    def restore_resume_states(self, states):
        assert set(states) == set(runner.ARMS)
        self._states = {arm: dict(states[arm]) for arm in runner.ARMS}

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        previous = world.episode_index - 1
        if previous == 0:
            assert resume_state is None
        else:
            assert resume_state["episode_index"] == previous
            assert resume_state["plan_sha256"] == plan_sha256
        arm_offset = runner.ARMS.index(arm)
        outcomes = [
            SimpleNamespace(
                link_rate_bps=np.full(
                    runner.USERS,
                    10.0 + (3 - arm_offset) + world.episode_index / 10_000 + step / 100,
                    dtype=np.float64,
                ),
                system_power_w=5.0 + step / 7 + arm_offset / 50,
                resolution=SimpleNamespace(served_count=runner.USERS - (step % 3)),
            )
            for step in range(runner.STEPS)
        ]
        aggregate = runner.aggregate_last_outcomes(outcomes, decision_interval_s=1.0)
        receipt = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA,
            status=runner.STATUS,
            split=runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=runner.USERS,
            steps=runner.STEPS,
            decision_interval_s=1.0,
            total_bits=float(aggregate["total_bits"]),
            total_energy_j=float(aggregate["total_energy_j"]),
            ratio_of_sums_ee_bits_per_j=float(aggregate["ratio_of_sums_ee_bits_per_j"]),
            served_user_steps=int(aggregate["served_user_steps"]),
            service_opportunities=int(aggregate["service_opportunities"]),
            service_fraction=float(aggregate["service_fraction"]),
            initial_world_sha256=runner.canonical_sha256(
                {"world_id": world.world_id, "world_seed": world.world_seed}
            ),
            field_component=runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256(
                {"arm": arm, "episode": world.episode_index}
            ),
            plan_sha256=plan_sha256,
            policy_binding=self._bindings[arm],
        )
        receipt.verify()
        self._states[arm] = {
            "arm": arm,
            "episode_index": world.episode_index,
            "plan_sha256": plan_sha256,
        }
        return receipt


class _FastHeldAdapter(_StubEvaluationAdapter):
    """Minimal deterministic episode transport for the full 3000 -> 9000 test."""

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        previous = world.episode_index - 1
        if previous == 0:
            assert resume_state is None
        else:
            assert resume_state["episode_index"] == previous
            assert resume_state["plan_sha256"] == plan_sha256
        bits = {"FULL2": 400.0, "DROP_C1": 300.0, "DROP_C2": 300.0, "BASELINE": 200.0}[arm]
        receipt = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA,
            status=runner.STATUS,
            split=runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=runner.USERS,
            steps=runner.STEPS,
            decision_interval_s=1.0,
            total_bits=bits,
            total_energy_j=10.0,
            ratio_of_sums_ee_bits_per_j=bits / 10.0,
            served_user_steps=runner.USERS * runner.STEPS,
            service_opportunities=runner.USERS * runner.STEPS,
            service_fraction=1.0,
            initial_world_sha256=runner.canonical_sha256(
                {"world_id": world.world_id, "world_seed": world.world_seed}
            ),
            field_component=runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256(
                {"arm": arm, "episode": world.episode_index}
            ),
            plan_sha256=plan_sha256,
            policy_binding=self._bindings[arm],
        )
        receipt.verify()
        self._states[arm] = {
            "arm": arm,
            "episode_index": world.episode_index,
            "plan_sha256": plan_sha256,
        }
        return receipt


def _admission_mapping(adapter) -> dict[str, dict[str, object]]:
    return {
        arm: {"policy_binding": adapter.policy_bindings[arm]}
        for arm in runner.ARMS
    }


def _evaluation(adapter, plan, **kwargs):
    return runner.FixedPolicyEvaluationRunner(
        adapter=adapter,
        plan=plan,
        admission_mapping=_admission_mapping(adapter),
        **kwargs,
    )


def test_checkpoint_and_rung_cadence_resume_100_to_500(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "run"
    first_adapter = _StubEvaluationAdapter()
    first = _evaluation(first_adapter, plan).run(output_dir=output, pause_at=100)
    assert first["completed_episode"] == 100
    assert first["terminal_result_emitted"] is False
    assert not (output / "result.json").exists()
    checkpoint = output / "checkpoints" / "checkpoint-000100.json"
    assert checkpoint.is_file()
    assert (output / "rungs" / "rung-000100.json").is_file()

    resumed_adapter = _StubEvaluationAdapter()
    resumed = _evaluation(resumed_adapter, plan).run(
        output_dir=output, pause_at=500, resume_checkpoint=checkpoint
    )
    assert resumed["completed_episode"] == 500
    assert resumed["receipt_count"] == 500 * len(runner.ARMS)
    assert resumed["terminal_result_emitted"] is False
    assert not (output / "result.json").exists()
    assert [path.name for path in sorted((output / "checkpoints").glob("*.json"))] == [
        f"checkpoint-{index:06d}.json" for index in range(100, 501, 100)
    ]
    assert [path.name for path in sorted((output / "rungs").glob("*.json"))] == [
        f"rung-{index:06d}.json" for index in range(100, 501, 100)
    ]


def test_resume_rejects_non_cadence_checkpoint_payload() -> None:
    plan = _plan()
    adapter = _StubEvaluationAdapter()
    evaluation = _evaluation(adapter, plan)
    payload = evaluation._checkpoint_payload(100, [])
    payload["completed_episode"] = 101
    with pytest.raises(runner.C1C2PhysicalError, match="100-episode cadence"):
        evaluation._validate_resume(payload)


def test_resume_rejects_root_with_terminal_result(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "terminal"
    output.mkdir()
    (output / "result.json").write_text("{}", encoding="ascii")
    with pytest.raises(runner.C1C2PhysicalError, match="terminal result"):
        adapter = _StubEvaluationAdapter()
        _evaluation(adapter, plan).run(
            output_dir=output,
            pause_at=500,
            resume_checkpoint=output / "checkpoints" / "checkpoint-000100.json",
        )
    assert (output / "integrity-stop.json").exists()


def test_9000_terminal_requires_later_authority() -> None:
    plan = _plan()
    with pytest.raises(runner.C1C2PhysicalError, match="continuation authority"):
        adapter = _StubEvaluationAdapter()
        _evaluation(adapter, plan, terminal_boundary=9000)


def test_sha_shaped_string_cannot_admit_9000() -> None:
    plan = _plan()
    with pytest.raises(runner.C1C2PhysicalError, match="sealed continuation authority file"):
        adapter = _StubEvaluationAdapter()
        _evaluation(
            adapter,
            plan,
            terminal_boundary=9000,
            continuation_authority_sha256="0" * 64,
        )


def test_resume_cross_checks_each_receipt_policy_binding(tmp_path: Path) -> None:
    plan = _plan()
    output = tmp_path / "run"
    adapter = _StubEvaluationAdapter()
    evaluation = _evaluation(adapter, plan)
    evaluation.run(output_dir=output, pause_at=100)
    checkpoint_path = output / "checkpoints" / "checkpoint-000100.json"
    payload = runner._read_json(checkpoint_path, label="checkpoint")
    payload["receipts"][0]["policy_binding"]["checkpoint_sha256"] = "f" * 64
    payload.pop("checkpoint_sha256")
    with pytest.raises(runner.C1C2PhysicalError, match="plan/policy binding"):
        rejecting_adapter = _StubEvaluationAdapter()
        _evaluation(rejecting_adapter, plan)._validate_resume(payload)


def _seal_json(path: Path, payload: dict[str, object]) -> str:
    runner._write_once(path, payload)
    digest = runner.file_sha256(path)
    path.with_name(path.name + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def test_held_3000_authority_admits_9000_core_runner_and_forgery_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "CHECKPOINT_EVERY", 3000)
    plan = _plan()
    adapter = _FastHeldAdapter()
    output = tmp_path / "run"
    result_3000 = _evaluation(adapter, plan, terminal_boundary=3000).run(
        output_dir=output, pause_at=3000
    )
    assert result_3000["overall_token"] == runner.HELD
    checkpoint = output / "checkpoints" / "checkpoint-003000.json"
    notification = output / "owner-notification.json"
    reply = "Owner authorizes the unchanged 9000-world continuation."
    _seal_json(
        notification,
        {
            "formal": True,
            "status": "OWNER_NOTIFIED_FOR_9000_CONTINUATION",
            "owner_reply_verbatim": reply,
            "notification_sent_utc": "2026-09-08T01:00:00Z",
            "owner_reply_received_utc": "2026-09-08T01:01:00Z",
            "notification_channel": "controller-chat",
            "recorded_by": "controller-test-session",
            "plan_sha256": plan.plan_sha256,
            "result_3000_sha256": runner.file_sha256(output / "result.json"),
        },
    )
    authority_path = output / "continuation-authority.json"
    authority = {
        "schema": runner.CONTINUATION_AUTHORITY_SCHEMA,
        "status": "AUTHORIZED_CONTINUATION_TO_9000",
        "continuation_from_episode": 3000,
        "continuation_to_episode": 9000,
        "plan_sha256": plan.plan_sha256,
        "policy_bindings_sha256": runner.canonical_sha256(adapter.policy_bindings),
        "held_terminal_token_sha256": runner.HELD_TOKEN_SHA256,
        "result_3000_sha256": runner.file_sha256(output / "result.json"),
        "checkpoint_3000_sha256": runner.file_sha256(checkpoint),
        "owner_reply_sha256": hashlib.sha256(reply.encode("utf-8")).hexdigest(),
        "recorded_by": "controller-test-session",
        "owner_notification": {
            "status": "OWNER_NOTIFIED",
            "path": str(notification.resolve()),
            "sha256": runner.file_sha256(notification),
        },
    }
    authority_sha = _seal_json(authority_path, authority)
    continuation_adapter = _FastHeldAdapter()
    evaluation = _evaluation(
        continuation_adapter,
        plan,
        terminal_boundary=9000,
        continuation_authority_path=authority_path,
        continuation_authority_sha256=authority_sha,
    )

    forged = dict(authority)
    forged["held_terminal_token_sha256"] = "f" * 64
    forged_path = output / "forged-authority.json"
    forged_sha = _seal_json(forged_path, forged)
    with pytest.raises(runner.C1C2PhysicalError, match="identity/bindings"):
        _evaluation(
            _FastHeldAdapter(),
            plan,
            terminal_boundary=9000,
            continuation_authority_path=forged_path,
            continuation_authority_sha256=forged_sha,
        )
    result_9000 = evaluation.run(
        output_dir=output,
        pause_at=9000,
        resume_checkpoint=checkpoint,
    )
    assert result_9000["completed_episode"] == 9000
    assert result_9000["terminal_result_emitted"] is True
    assert (output / "continuation-result.json").is_file()


def _rngs(seed: int):
    sequence = np.random.SeedSequence(seed)
    children = sequence.spawn(2)
    return np.random.default_rng(children[0]), np.random.default_rng(children[1])


class _ChunkTransportStub:
    """Fast persistence/merge transport stub; never acceptance evidence."""

    def __init__(self, arm: str, *, interrupt_after: int | None = None) -> None:
        self.arm = arm
        self.rng_factory = _rngs
        self.interrupt_after = interrupt_after
        self.calls = 0
        self._binding = {
            "arm": arm,
            "routes": [] if arm == "BASELINE" else ["C1", "C2"],
            "checkpoint_sha256": runner.canonical_sha256({"arm": arm, "fixture": "age-stream"}),
            "fixed_policy": True,
        }
        self._state = None
        self.archive = object()
        self.environment_factory = self._environment_factory

    @staticmethod
    def _environment_factory(_archive, _users):
        environment = object.__new__(TrainerEnvironment)
        environment.environment = SimpleNamespace(
            physics=SimpleNamespace(segment_warm_start="uniform-episode-length")
        )
        return environment

    @property
    def policy_bindings(self):
        return {self.arm: self._binding}

    def resume_state_for(self, arm):
        assert arm == self.arm
        return self._state

    def run_episode(self, *, arm, world, plan_sha256, resume_state=None):
        assert arm == self.arm
        if self.interrupt_after is not None and self.calls == self.interrupt_after:
            raise KeyboardInterrupt("fixture interruption")
        self.calls += 1
        if resume_state is None:
            age_rng = _rngs(world.world_seed)[0].spawn(1)[0]
        else:
            age_rng = np.random.default_rng()
            age_rng.bit_generator.state = resume_state["environment_training_state"]["age_rng_state"]
        ages = age_rng.integers(0, runner.STEPS, size=runner.USERS)
        bits = float(math.fsum(float(value + 1) for value in ages))
        energy = float(runner.USERS + world.episode_index / 10_000)
        receipt = runner.EpisodeReceipt(
            schema=runner.RECEIPT_SCHEMA,
            status=runner.STATUS,
            split=runner.SPLIT,
            arm=arm,
            routes=() if arm == "BASELINE" else runner.ROUTES,
            episode_index=world.episode_index,
            world_id=world.world_id,
            world_seed=world.world_seed,
            users=runner.USERS,
            steps=runner.STEPS,
            decision_interval_s=1.0,
            total_bits=bits,
            total_energy_j=energy,
            ratio_of_sums_ee_bits_per_j=bits / energy,
            served_user_steps=runner.USERS * runner.STEPS,
            service_opportunities=runner.USERS * runner.STEPS,
            service_fraction=1.0,
            initial_world_sha256=runner.canonical_sha256({"ages": ages}),
            field_component=runner.FIELD_COMPONENT,
            field_root_digest=world.field_root_digest,
            action_trace_sha256=runner.canonical_sha256({"ages": ages, "arm": arm}),
            plan_sha256=plan_sha256,
            policy_binding=self._binding,
        )
        receipt.verify()
        self._state = {
            "schema": f"{runner.SCHEMA}-resume-state",
            "arm": arm,
            "episode_index": world.episode_index,
            "world_id": world.world_id,
            "world_seed": world.world_seed,
            "field_root_digest": world.field_root_digest,
            "plan_sha256": plan_sha256,
            "policy_binding": self._binding,
            "environment_training_state": {
                "format_version": 1,
                "age_rng_state": age_rng.bit_generator.state,
            },
        }
        return receipt


def _chunk_context(adapter: _ChunkTransportStub) -> dict[str, object]:
    digests = {
        name: runner.canonical_sha256({"fixture": name})
        for name in (
            "authority_sha256",
            "code_manifest_sha256",
            "configuration_sha256",
            "tle_sha256",
            "prereg_sha256",
            "admission_sha256",
            "stage_ab_supplement_sha256",
            "acceptance_evidence_sha256",
            "acceptance_procedure_sha256",
        )
    }
    arm = getattr(adapter, "arm", next(iter(adapter.policy_bindings)))
    return {
        "arm": arm,
        "adapter": adapter,
        "schedule_sha256": runner.canonical_sha256({"schedule": "fixture"}),
        "execution_mode": "arm_decoupled",
        "continuation_limit": 3000,
        "provenance": digests,
    }


def _direct_sequential(plan, adapter, episodes=200):
    rows = []
    state = None
    states = {}
    arm = getattr(adapter, "arm", next(iter(adapter.policy_bindings)))
    for index in range(episodes):
        row = adapter.run_episode(
            arm=arm,
            world=plan.worlds[index],
            plan_sha256=plan.plan_sha256,
            resume_state=state,
        )
        rows.append(row)
        state = adapter.resume_state_for(arm)
        if index + 1 in {100, 200} or episodes <= 2:
            states[index + 1] = json.loads(json.dumps(runner._jsonable(state)))
    return rows, states


@pytest.mark.parametrize("arm", runner.ARMS)
def test_synthetic_transport_preserves_two_100_chunk_values(
    arm: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan = _plan()
    sequential_rows, sequential_states = _direct_sequential(plan, _ChunkTransportStub(arm))
    adapter = _ChunkTransportStub(arm)
    table_a = runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 100, 200))
    table_b = runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 100, 200))
    assert {key: value.as_dict() for key, value in table_a.items()} == {
        key: value.as_dict() for key, value in table_b.items()
    }
    assert table_a[100]["resume_state"] == sequential_states[100]
    assert table_a[200]["resume_state"] == sequential_states[200]
    first_root = tmp_path / f"{arm}-0-100"
    second_root = tmp_path / f"{arm}-100-200"
    runner.run_arm_chunk(arm, 0, 100, table_a[0], first_root)
    runner.run_arm_chunk(arm, 100, 200, table_a[100], second_root)
    chunk_rows = []
    for root, start, end in ((first_root, 0, 100), (second_root, 100, 200)):
        for episode in range(start + 1, end + 1):
            row, _state = runner._read_episode_record(root / "episodes" / f"episode-{episode:06d}.json")
            chunk_rows.append(row)
    assert [row.as_dict() for row in chunk_rows] == [row.as_dict() for row in sequential_rows]
    for boundary in (100, 200):
        sequential_pool = runner.pool_receipts(sequential_rows[:boundary], arm=arm)
        chunk_pool = runner.pool_receipts(chunk_rows[:boundary], arm=arm)
        assert runner._canonical_bytes(sequential_pool) == runner._canonical_bytes(chunk_pool)
    merged = runner.merge_arm_chunks(arm, (first_root, second_root), tmp_path / f"{arm}-merged")
    assert merged["ordered_episode_digest"] == runner.canonical_sha256(
        [row.as_dict() for row in sequential_rows]
    )
    with pytest.raises(runner.C1C2PhysicalError, match="duplicate completed chunk"):
        runner.run_arm_chunk(arm, 0, 100, table_a[0], first_root)


def test_chunk_interruption_preserves_prefix_and_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan = _plan()
    adapter = _ChunkTransportStub("BASELINE", interrupt_after=17)
    table = runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 100))
    root = tmp_path / "interrupted"
    with pytest.raises(KeyboardInterrupt):
        runner.run_arm_chunk("BASELINE", 0, 100, table[0], root)
    assert len(list((root / "episodes").glob("episode-*.json"))) == 17
    first_started = runner._read_json(
        root / "attempts/attempt-000001.json", label="first attempt"
    )["started_utc"]
    adapter.interrupt_after = None
    receipt = runner.run_arm_chunk("BASELINE", 0, 100, table[0], root)
    assert receipt["status"] == "COMPLETE_ARM_CHUNK"
    assert len(list((root / "episodes").glob("episode-*.json"))) == 100
    assert receipt["started_utc"] == first_started
    assert len(receipt["execution_attempts"]) == 2


def test_second_chunk_repairs_failed_terminal_checkpoint_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan = _plan()
    adapter = _ChunkTransportStub("BASELINE")
    context = _chunk_context(adapter)
    table = runner.build_chunk_boundary_states(plan, context, (0, 100, 200))
    root = tmp_path / "BASELINE-000100-000200"
    original_write = runner._write_once
    failed = False

    def fail_terminal_checkpoint(path, payload):
        nonlocal failed
        target = Path(path)
        if target.name == "checkpoint-000200.json" and not failed:
            failed = True
            raise OSError("simulated checkpoint publication failure")
        return original_write(target, payload)

    monkeypatch.setattr(runner, "_write_once", fail_terminal_checkpoint)
    with pytest.raises(OSError, match="simulated checkpoint publication failure"):
        runner.run_arm_chunk("BASELINE", 100, 200, table[100], root)
    monkeypatch.setattr(runner, "_write_once", original_write)
    assert len(list((root / "episodes").glob("episode-*.json"))) == 100
    rows = [
        runner._read_episode_record(path)[0].as_dict()
        for path in sorted((root / "episodes").glob("episode-*.json"))
    ]
    stop = root / "integrity-stop.json"
    authority = tmp_path / "repair-authority.json"
    authority_sha = _seal_json(
        authority,
        {
            "schema": runner.REPAIR_AUTHORITY_SCHEMA,
            "status": "AUTHORIZED_INFRASTRUCTURE_REPAIR",
            "plan_sha256": plan.plan_sha256,
            "chunk_id": "BASELINE-000100-000200",
            "chunk_root": str(root.resolve()),
            "prefix_episode": 200,
            "prefix_digest": runner.canonical_sha256(rows),
            "integrity_stop_sha256": runner.file_sha256(stop),
            "preserve_valid_history": True,
            "smallest_invalid_unit": "checkpoint-publication",
        },
    )
    repair_context = {
        **context,
        "repair_authority_path": authority,
        "repair_authority_sha256": authority_sha,
    }
    repair_state = runner.ChunkBoundaryState(
        table[100].payload,
        table[100].plan,
        table[100].adapter,
        repair_context,
        table[100].table_payloads,
    )
    receipt = runner.run_arm_chunk("BASELINE", 100, 200, repair_state, root)
    assert receipt["status"] == "COMPLETE_ARM_CHUNK"
    assert receipt["range"] == [101, 200]
    assert (root / "repair-receipt.json").is_file()


def test_nonformal_50_alignment_is_narrow_and_cannot_merge_formally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan = _plan()
    adapter = _ChunkTransportStub("FULL2")
    context = _chunk_context(adapter)
    context.update({
        "formal": False,
        "acceptance_mode": "NONFORMAL_EQUIVALENCE_REHEARSAL",
        "chunk_alignment": 50,
    })
    table = runner.build_chunk_boundary_states(plan, context, (0, 50, 100))
    first = tmp_path / "FULL2-000000-000050"
    second = tmp_path / "FULL2-000050-000100"
    assert runner.run_arm_chunk("FULL2", 0, 50, table[0], first)["formal"] is False
    assert runner.run_arm_chunk("FULL2", 50, 100, table[50], second)["formal"] is False
    with pytest.raises(runner.C1C2PhysicalError, match="identity"):
        runner.merge_arm_chunks("FULL2", (first, second), tmp_path / "formal-merge")
    merged = runner.merge_arm_chunks(
        "FULL2", (first, second), tmp_path / "acceptance-merge",
        formal_required=False,
    )
    assert merged["formal"] is False
    assert [path.name for path in sorted((tmp_path / "acceptance-merge/checkpoints").glob("*.json"))] == [
        "checkpoint-000050.json", "checkpoint-000100.json"
    ]
    assert [path.name for path in sorted((tmp_path / "acceptance-merge/rungs").glob("*.json"))] == [
        "rung-000050.json", "rung-000100.json"
    ]
    context.pop("acceptance_mode")
    with pytest.raises(runner.C1C2PhysicalError, match="explicit non-formal"):
        runner.build_chunk_boundary_states(plan, context, (0, 50, 100))


def test_boundary_builder_fails_closed_for_other_warm_start_mode() -> None:
    plan = _plan()
    adapter = _ChunkTransportStub("BASELINE")

    def wrong_mode(_archive, _users):
        environment = object.__new__(TrainerEnvironment)
        environment.environment = SimpleNamespace(
            physics=SimpleNamespace(segment_warm_start="uniform-segment-length")
        )
        return environment

    adapter.environment_factory = wrong_mode
    with pytest.raises(runner.C1C2PhysicalError, match="segment_warm_start"):
        runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 100))


def test_merge_rejects_stale_indexed_episode_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    plan = _plan()
    adapter = _ChunkTransportStub("BASELINE")
    table = runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 100))
    root = tmp_path / "BASELINE-000000-000100"
    runner.run_arm_chunk("BASELINE", 0, 100, table[0], root)
    record = root / "episodes/episode-000001.json"
    record.write_bytes(record.read_bytes() + b" ")
    with pytest.raises(runner.C1C2PhysicalError, match="indexed episode hash"):
        runner.merge_arm_chunks("BASELINE", (root,), tmp_path / "merged")


def test_real_environment_sequential_equals_chunked_bitwise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise the retained adapter and real Step/Trainer environment, not an age stub."""

    import struct
    from mcrl.env.constants import TLE_ROOT_DEFAULT
    from mcrl.env.ephemeris import TRAIN, BlockAlternatingSplit, EpisodeStartSampler
    from mcrl.env.mobility import MobilityConfig
    from mcrl.env.scenario import ScenarioConfig, ScenarioDriver
    from mcrl.env.step import StepEnvironment
    from mcrl.env.tle import TleArchive

    for name in runner.NUMERICAL_THREAD_ENV:
        monkeypatch.setenv(name, "1")
    archive = TleArchive(Path(TLE_ROOT_DEFAULT).expanduser())

    def environment_factory(bound_archive, users):
        driver = ScenarioDriver(
            bound_archive,
            ScenarioConfig(mobility=MobilityConfig(num_users=users)),
        )
        split = BlockAlternatingSplit.for_archive(bound_archive)
        sampler = EpisodeStartSampler.for_archive(bound_archive, split, TRAIN)
        return TrainerEnvironment(StepEnvironment(driver), sampler)

    plan = _plan()
    policy = runner.load_baseline_policy(
        checkpoint_path=HERE.parents[1] / "artifacts/training-2026-08-25-rerun01/main/final-checkpoint.pt",
        status_path=HERE.parents[1] / "artifacts/training-2026-08-25-rerun01/main/status.json",
        expected_status_sha256=runner.file_sha256(
            HERE.parents[1] / "artifacts/training-2026-08-25-rerun01/main/status.json"
        ),
    )
    sampler_sha = runner.canonical_sha256(environment_factory(archive, runner.USERS).sampler.as_dict())
    sources = {
        "FULL2": ["informed", "informed"],
        "DROP_C1": ["neutral", "informed"],
        "DROP_C2": ["informed", "neutral"],
    }
    admission_path = tmp_path / "runtime-admission.json"
    admission_payload = {
        "schema": f"{runner.SCHEMA}-runtime-admission-v1",
        "status": "FORMAL_RUNTIME_ADMITTED",
        "split": runner.SPLIT,
        "admitted_evaluation_sha256": plan.plan_sha256,
        "sampler": {"part": "train", "as_dict_sha256": sampler_sha},
        "learned_training_provenance": {
            arm: {
                "arm": arm,
                "checkpoint_sha256": runner.canonical_sha256({"fixture": arm}),
                "source_mapping": sources[arm],
                "stage_a_status": "PASS_SOURCE_TRAINING_INTEGRITY",
                "manifest_sha256": "a" * 64,
            }
            for arm in runner.LEARNED_ARMS
        },
        "predecessor_pass_receipts": [],
    }
    admission_sha = _seal_json(admission_path, admission_payload)
    admission = {
        **admission_payload,
        "admission_path": str(admission_path.resolve()),
        "admission_sha256": admission_sha,
        "authenticated_predecessor_statuses": [
            "PASS_SOURCE_TRAINING_INTEGRITY", "PASS_PLUMBING_INTEGRITY"
        ],
    }

    def adapter():
        return runner.FixedPolicyEpisodeAdapter(
            policies=(policy,), archive=archive,
            environment_factory=environment_factory, rng_factory=_rngs,
            runtime_admission=admission,
        )

    direct_rows, direct_states = _direct_sequential(plan, adapter(), episodes=2)
    chunk_adapter = adapter()
    context = _chunk_context(chunk_adapter)
    context.update({
        "formal": False,
        "acceptance_mode": "NONFORMAL_EQUIVALENCE_REHEARSAL",
        "chunk_alignment": 1,
    })
    table = runner.build_chunk_boundary_states(plan, context, (0, 1, 2))
    roots = (tmp_path / "real-0-1", tmp_path / "real-1-2")
    runner.run_arm_chunk("BASELINE", 0, 1, table[0], roots[0])
    runner.run_arm_chunk("BASELINE", 1, 2, table[1], roots[1])
    chunk_rows = [
        runner._read_episode_record(root / f"episodes/episode-{episode:06d}.json")[0]
        for root, episode in zip(roots, (1, 2), strict=True)
    ]

    def bitwise(left, right):
        if isinstance(left, float) or isinstance(right, float):
            return isinstance(left, float) and isinstance(right, float) and struct.pack(">d", left) == struct.pack(">d", right)
        if isinstance(left, dict) and isinstance(right, dict):
            return set(left) == set(right) and all(bitwise(left[key], right[key]) for key in left)
        if isinstance(left, list) and isinstance(right, list):
            return len(left) == len(right) and all(bitwise(a, b) for a, b in zip(left, right, strict=True))
        return left == right

    assert bitwise([row.as_dict() for row in direct_rows], [row.as_dict() for row in chunk_rows])
    assert table[1]["resume_state"] == direct_states[1]
    assert table[2]["resume_state"] == direct_states[2]


def test_chunk_refuses_early_baseline_above_3000_and_missing_fourth_arm(
    tmp_path: Path,
) -> None:
    plan = _plan()
    adapter = _ChunkTransportStub("BASELINE")
    with pytest.raises(runner.C1C2PhysicalError, match="continuation authority"):
        runner.build_chunk_boundary_states(plan, _chunk_context(adapter), (0, 3100))
    with pytest.raises(runner.C1C2PhysicalError, match="every arm"):
        runner.merge_four_arm(
            {arm: tmp_path / arm for arm in runner.ARMS[:-1]},
            tmp_path / "four",
            admission_mapping={arm: {} for arm in runner.ARMS},
        )
