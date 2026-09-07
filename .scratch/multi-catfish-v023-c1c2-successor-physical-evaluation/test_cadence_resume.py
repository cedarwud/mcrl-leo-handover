from __future__ import annotations

import hashlib
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
